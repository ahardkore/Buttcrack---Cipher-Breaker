#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 504
#define COLS 42
#define ROWS 12
#define ZONE_START 18
#define ZONE_END 32
#define ZONE_LEN (ZONE_END - ZONE_START + 1)

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const int base_q7[7] = {0, 9, 5, 17, 10, 2, 24};
static const int base_q8[8] = {0, 8, 16, 15, 16, 3, 6, 20};
static const int base_q9[9] = {16, 0, 19, 9, 7, 23, 6, 16, 18};

static const int initial_order[COLS] = {
    29, 1, 34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16, // 0..17 (Fixed)
    20, 37, 39, 7, 31, 33, 32, 36, 22, 35, 27, 10, 9,                   // 18..28
    41, 8, 19, 11, 18, 14, 6, 24, 5, 4, 40                              // 29..41 (Wait: let's verify exact indices)
};

static float qtable[26][26][26][26];
static char valid_q[26][26][26][26];

static void load_quads(void) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    qtable[a][b][c][d] = -9.5f;
                    valid_q[a][b][c][d] = 0;
                }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { fprintf(stderr, "Missing english_quads.tsv\n"); exit(1); }
    char buf[64];
    while (fgets(buf, sizeof(buf), f)) {
        char q[5]; float sc;
        if (sscanf(buf, "%4s %f", q, &sc) == 2) {
            int a = q[0] - 'A', b = q[1] - 'A', c = q[2] - 'A', d = q[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                qtable[a][b][c][d] = sc;
                valid_q[a][b][c][d] = 1;
            }
        }
    }
    fclose(f);
}

static inline void eval_grid(const char cols[COLS][ROWS], const int order[COLS], float *out_sc, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c <= COLS - 4; c++) {
            int a = cols[order[c]][r] - 'A';
            int b = cols[order[c+1]][r] - 'A';
            int c_char = cols[order[c+2]][r] - 'A';
            int d = cols[order[c+3]][r] - 'A';
            sc += qtable[a][b][c_char][d];
            if (!valid_q[a][b][c_char][d]) def++;
        }
    }
    *out_sc = sc / 468.0f;
    *out_def = def;
}

int main(void) {
    load_quads();
    
    // Exact base order from record:
    int base_order[COLS] = {
        29, 1, 34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16,
        20, 37, 39, 7, 31, 33, 32, 36, 22, 35, 27, 10, 9,
        41, 8, 19, 11, 18, 14, 6, 24, 5, 4, 40
    };

    // Precompute Z
    char Z[N];
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int shift = (base_q7[i%7] + base_q8[i%8] + base_q9[i%9]) % 26;
        int pt_idx = (ct_idx - shift + 26) % 26;
        Z[i] = KRYPTOS[pt_idx];
    }

    char cols[COLS][ROWS];
    for (int c = 0; c < COLS; c++) {
        for (int r = 0; r < ROWS; r++) {
            cols[c][r] = Z[c * ROWS + r];
        }
    }

    float init_sc; int init_def;
    eval_grid(cols, base_order, &init_sc, &init_def);
    printf("Initial Record: Score = %.4f | Defects = %d / 468\n", init_sc, init_def);

    // Global best
    float global_best_sc = init_sc;
    int global_best_def = init_def;
    int global_best_order[COLS];
    memcpy(global_best_order, base_order, sizeof(base_order));

    int num_threads = omp_get_max_threads();
    printf("Running Defect Zone Simulated Annealing across %d threads...\n", num_threads);

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 1013;
        int cur_order[COLS];
        memcpy(cur_order, base_order, sizeof(base_order));

        float cur_sc = init_sc;
        int cur_def = init_def;

        float best_local_sc = cur_sc;
        int best_local_def = cur_def;
        int best_local_order[COLS];
        memcpy(best_local_order, cur_order, sizeof(cur_order));

        int total_steps = 1500000;
        float T_start = 0.5f;
        float T_end = 0.001f;

        for (int step = 0; step < total_steps; step++) {
            float frac = (float)step / (float)total_steps;
            float T = T_start * powf(T_end / T_start, frac);

            int next_order[COLS];
            memcpy(next_order, cur_order, sizeof(cur_order));

            // Move inside zone [18..31] (14 columns)
            int z_len = 14;
            int z_start = 18;
            int move_type = rand_r(&seed) % 3;
            int i = z_start + (rand_r(&seed) % z_len);
            int j = z_start + (rand_r(&seed) % z_len);

            if (move_type == 0) {
                // Swap
                int tmp = next_order[i];
                next_order[i] = next_order[j];
                next_order[j] = tmp;
            } else if (move_type == 1) {
                // 2-opt inversion
                if (i > j) { int t = i; i = j; j = t; }
                while (i < j) {
                    int tmp = next_order[i];
                    next_order[i] = next_order[j];
                    next_order[j] = tmp;
                    i++; j--;
                }
            } else {
                // Insertion
                int val = next_order[i];
                if (i < j) {
                    for (int k = i; k < j; k++) next_order[k] = next_order[k+1];
                    next_order[j] = val;
                } else if (i > j) {
                    for (int k = i; k > j; k--) next_order[k] = next_order[k-1];
                    next_order[j] = val;
                }
            }

            float next_sc; int next_def;
            eval_grid(cols, next_order, &next_sc, &next_def);

            // Objective: prioritize defects, then quadgram score
            float d_fit = (cur_def - next_def) * 1.5f + (next_sc - cur_sc);

            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / (float)RAND_MAX))) {
                memcpy(cur_order, next_order, sizeof(cur_order));
                cur_sc = next_sc;
                cur_def = next_def;

                if (cur_def < best_local_def || (cur_def == best_local_def && cur_sc > best_local_sc)) {
                    best_local_def = cur_def;
                    best_local_sc = cur_sc;
                    memcpy(best_local_order, cur_order, sizeof(cur_order));
                }
            }
        }

        #pragma omp critical
        {
            if (best_local_def < global_best_def || (best_local_def == global_best_def && best_local_sc > global_best_sc)) {
                global_best_def = best_local_def;
                global_best_sc = best_local_sc;
                memcpy(global_best_order, best_local_order, sizeof(best_local_order));
                printf("[Thread %d] NEW RECORD: Score = %.4f | Defects = %d / 468\n",
                       omp_get_thread_num(), global_best_sc, global_best_def);
            }
        }
    }

    printf("\n--- FINAL RESULT ---\n");
    printf("Best Score: %.4f | Best Defects: %d / 468 (%.1f%% valid)\n",
           global_best_sc, global_best_def, (468 - global_best_def) / 468.0f * 100.0f);
    printf("Order: [");
    for (int i = 0; i < COLS; i++) printf("%d%s", global_best_order[i], i == COLS-1 ? "" : ", ");
    printf("]\n");

    return 0;
}

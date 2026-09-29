#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 504
#define COLS 42
#define ROWS 12
#define CORE_COLS 36
#define ZONE_START 18
#define ZONE_LEN 14

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const int base_q7[7] = {0, 9, 5, 17, 10, 2, 24};
static const int base_q8[8] = {0, 8, 16, 15, 16, 3, 6, 20};
static const int base_q9[9] = {16, 0, 19, 9, 7, 23, 6, 16, 18};

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

static inline void eval_core_order(const char cols[COLS][ROWS], const int order[CORE_COLS], float *out_sc, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c <= CORE_COLS - 4; c++) {
            int a = cols[order[c]][r] - 'A';
            int b = cols[order[c+1]][r] - 'A';
            int c_char = cols[order[c+2]][r] - 'A';
            int d = cols[order[c+3]][r] - 'A';
            sc += qtable[a][b][c_char][d];
            if (!valid_q[a][b][c_char][d]) def++;
        }
    }
    *out_sc = sc / 396.0f;
    *out_def = def;
}

int main(void) {
    load_quads();

    // Precompute Z and columns
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

    // Baseline 36 core columns
    int base_core[CORE_COLS] = {
        34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16, 20, 37, // 0..17 (Fixed)
        39, 7, 31, 33, 32, 36, 22, 35, 27, 10, 9, 41, 8, 19,                 // 18..31 (Zone: 14 cols)
        11, 18, 14, 6                                                         // 32..35 (Fixed)
    };

    float base_sc; int base_def;
    eval_core_order(cols, base_core, &base_sc, &base_def);
    printf("Initial Core Baseline: Score = %.4f | Defects = %d / 396 (%.1f%% valid)\n",
           base_sc, base_def, (396 - base_def)/396.0f * 100.0f);

    float global_best_sc = base_sc;
    int global_best_def = base_def;
    int global_best_core[CORE_COLS];
    memcpy(global_best_core, base_core, sizeof(base_core));

    int num_threads = omp_get_max_threads();
    printf("Executing 14-Column Branch & Bound SA across %d threads (2,500,000 steps/thread)...\n", num_threads);

    #pragma omp parallel
    {
        unsigned int seed = 98765 + omp_get_thread_num() * 24680;
        int cur_core[CORE_COLS];
        memcpy(cur_core, base_core, sizeof(base_core));
        float cur_sc = base_sc;
        int cur_def = base_def;

        int local_best_core[CORE_COLS];
        memcpy(local_best_core, base_core, sizeof(base_core));
        float local_best_sc = base_sc;
        int local_best_def = base_def;

        int steps = 2500000;
        float T_start = 0.4f, T_end = 0.0005f;

        for (int s = 0; s < steps; s++) {
            float frac = (float)s / steps;
            float T = T_start * powf(T_end / T_start, frac);

            int next_core[CORE_COLS];
            memcpy(next_core, cur_core, sizeof(cur_core));

            // Permute strictly in zone [ZONE_START .. ZONE_START + ZONE_LEN - 1] = [18..31]
            int m = rand_r(&seed) % 3;
            int i = ZONE_START + (rand_r(&seed) % ZONE_LEN);
            int j = ZONE_START + (rand_r(&seed) % ZONE_LEN);

            if (m == 0) {
                int tmp = next_core[i]; next_core[i] = next_core[j]; next_core[j] = tmp;
            } else if (m == 1) {
                if (i > j) { int t = i; i = j; j = t; }
                while (i < j) {
                    int tmp = next_core[i]; next_core[i] = next_core[j]; next_core[j] = tmp;
                    i++; j--;
                }
            } else {
                int val = next_core[i];
                if (i < j) {
                    for (int k = i; k < j; k++) next_core[k] = next_core[k+1];
                    next_core[j] = val;
                } else if (i > j) {
                    for (int k = i; k > j; k--) next_core[k] = next_core[k-1];
                    next_core[j] = val;
                }
            }

            float next_sc; int next_def;
            eval_core_order(cols, next_core, &next_sc, &next_def);

            float d_fit = (cur_def - next_def) * 1.5f + (next_sc - cur_sc);
            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                memcpy(cur_core, next_core, sizeof(cur_core));
                cur_sc = next_sc;
                cur_def = next_def;

                if (cur_def < local_best_def || (cur_def == local_best_def && cur_sc > local_best_sc)) {
                    local_best_def = cur_def;
                    local_best_sc = cur_sc;
                    memcpy(local_best_core, cur_core, sizeof(cur_core));
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_def < global_best_def || (local_best_def == global_best_def && local_best_sc > global_best_sc)) {
                global_best_def = local_best_def;
                global_best_sc = local_best_sc;
                memcpy(global_best_core, local_best_core, sizeof(local_best_core));
                printf("[Thread %d] NEW RECORD FROM 14-COL SA: Score = %.4f | Defects = %d / 396 (%.1f%% valid)\n",
                       omp_get_thread_num(), global_best_sc, global_best_def, (396 - global_best_def)/396.0f * 100.0f);
            }
        }
    }

    printf("\n======================================================\n");
    printf("FINAL 14-COLUMN BRANCH & BOUND RESULT:\n");
    printf("Score: %.4f | Defects: %d / 396 (%.1f%% valid)\n",
           global_best_sc, global_best_def, (396 - global_best_def)/396.0f * 100.0f);
    printf("Baseline: Score = %.4f | Defects = %d / 396 (%.1f%% valid)\n",
           base_sc, base_def, (396 - base_def)/396.0f * 100.0f);

    printf("Optimal 14-Column Sector [18..31]:\n[");
    for (int i = ZONE_START; i < ZONE_START + ZONE_LEN; i++)
        printf("%d%s", global_best_core[i], i == ZONE_START + ZONE_LEN - 1 ? "" : ", ");
    printf("]\n");

    return 0;
}

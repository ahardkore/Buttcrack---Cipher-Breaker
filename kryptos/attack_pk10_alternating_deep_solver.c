#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 504
#define COLS 42
#define ROWS 12

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

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

static inline void compute_grid(const int q7[7], const int q8[8], const int q9[9], char cols[COLS][ROWS]) {
    char Z[N];
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int shift = (q7[i%7] + q8[i%8] + q9[i%9]) % 26;
        int pt_idx = (ct_idx - shift + 26) % 26;
        Z[i] = KRYPTOS[pt_idx];
    }
    for (int c = 0; c < COLS; c++) {
        for (int r = 0; r < ROWS; r++) {
            cols[c][r] = Z[c * ROWS + r];
        }
    }
}

static inline void eval_grid_order(const char cols[COLS][ROWS], const int order[COLS], float *out_sc, int *out_def) {
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

    int q7[7] = {0, 9, 5, 17, 10, 2, 24};
    int q8[8] = {0, 8, 16, 15, 16, 3, 6, 20};
    int q9[9] = {16, 0, 19, 9, 7, 23, 6, 16, 18};

    int order[COLS] = {
        29, 1, 34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16,
        20, 37, 39, 7, 31, 33, 32, 36, 22, 35, 27, 10, 9,
        41, 8, 19, 11, 18, 14, 6, 24, 5, 4, 40
    };

    char cols[COLS][ROWS];
    compute_grid(q7, q8, q9, cols);

    float cur_sc; int cur_def;
    eval_grid_order(cols, order, &cur_sc, &cur_def);
    printf("Initial Record State: Score = %.4f | Defects = %d / 468 (%.1f%% valid)\n",
           cur_sc, cur_def, (468 - cur_def)/468.0f * 100.0f);

    int outer_cycles = 10;
    for (int cycle = 1; cycle <= outer_cycles; cycle++) {
        printf("\n=== Outer Alternating Cycle %d / %d ===\n", cycle, outer_cycles);

        // Stage A: OpenMP TSP Simulated Annealing on Column Order
        printf("Stage A: TSP Annealing on 42 Columns...\n");
        int best_local_order[COLS];
        memcpy(best_local_order, order, sizeof(order));
        float best_local_sc = cur_sc;
        int best_local_def = cur_def;

        #pragma omp parallel
        {
            unsigned int seed = 54321 + omp_get_thread_num() * 1999 + cycle * 37;
            int cur_t_order[COLS];
            memcpy(cur_t_order, order, sizeof(order));
            float t_sc = cur_sc;
            int t_def = cur_def;

            int my_best_order[COLS];
            memcpy(my_best_order, order, sizeof(order));
            float my_best_sc = cur_sc;
            int my_best_def = cur_def;

            int steps = 200000;
            float T_start = 0.3f, T_end = 0.001f;

            for (int s = 0; s < steps; s++) {
                float frac = (float)s / steps;
                float T = T_start * powf(T_end / T_start, frac);

                int next_order[COLS];
                memcpy(next_order, cur_t_order, sizeof(cur_t_order));

                int m = rand_r(&seed) % 3;
                int i = rand_r(&seed) % COLS;
                int j = rand_r(&seed) % COLS;

                if (m == 0) {
                    int tmp = next_order[i]; next_order[i] = next_order[j]; next_order[j] = tmp;
                } else if (m == 1) {
                    if (i > j) { int t = i; i = j; j = t; }
                    while (i < j) {
                        int tmp = next_order[i]; next_order[i] = next_order[j]; next_order[j] = tmp;
                        i++; j--;
                    }
                } else {
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
                eval_grid_order(cols, next_order, &next_sc, &next_def);

                float d_fit = (t_def - next_def) * 1.5f + (next_sc - t_sc);
                if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                    memcpy(cur_t_order, next_order, sizeof(cur_t_order));
                    t_sc = next_sc;
                    t_def = next_def;

                    if (t_def < my_best_def || (t_def == my_best_def && t_sc > my_best_sc)) {
                        my_best_def = t_def;
                        my_best_sc = t_sc;
                        memcpy(my_best_order, cur_t_order, sizeof(cur_t_order));
                    }
                }
            }

            #pragma omp critical
            {
                if (my_best_def < best_local_def || (my_best_def == best_local_def && my_best_sc > best_local_sc)) {
                    best_local_def = my_best_def;
                    best_local_sc = my_best_sc;
                    memcpy(best_local_order, my_best_order, sizeof(my_best_order));
                }
            }
        }

        if (best_local_def < cur_def || (best_local_def == cur_def && best_local_sc > cur_sc)) {
            cur_def = best_local_def;
            cur_sc = best_local_sc;
            memcpy(order, best_local_order, sizeof(order));
            printf("  Stage A Result: NEW RECORD Score = %.4f | Defects = %d / 468\n", cur_sc, cur_def);
        } else {
            printf("  Stage A Result: Order stationary (Score = %.4f | Defects = %d)\n", cur_sc, cur_def);
        }

        // Stage B: Clock Coordinate Descent across all 24 coordinates
        printf("Stage B: Sweeping all 24 Clock Coordinates...\n");
        int clock_improved = 0;

        for (int i = 0; i < 7; i++) {
            int orig = q7[i]; int best_v = orig;
            for (int v = 0; v < 26; v++) {
                q7[i] = v;
                char test_cols[COLS][ROWS];
                compute_grid(q7, q8, q9, test_cols);
                float sc; int def;
                eval_grid_order(test_cols, order, &sc, &def);
                if (def < cur_def || (def == cur_def && sc > cur_sc + 1e-5f)) {
                    cur_def = def; cur_sc = sc; best_v = v; clock_improved = 1;
                }
            }
            q7[i] = best_v;
        }

        for (int i = 0; i < 8; i++) {
            int orig = q8[i]; int best_v = orig;
            for (int v = 0; v < 26; v++) {
                q8[i] = v;
                char test_cols[COLS][ROWS];
                compute_grid(q7, q8, q9, test_cols);
                float sc; int def;
                eval_grid_order(test_cols, order, &sc, &def);
                if (def < cur_def || (def == cur_def && sc > cur_sc + 1e-5f)) {
                    cur_def = def; cur_sc = sc; best_v = v; clock_improved = 1;
                }
            }
            q8[i] = best_v;
        }

        for (int i = 0; i < 9; i++) {
            int orig = q9[i]; int best_v = orig;
            for (int v = 0; v < 26; v++) {
                q9[i] = v;
                char test_cols[COLS][ROWS];
                compute_grid(q7, q8, q9, test_cols);
                float sc; int def;
                eval_grid_order(test_cols, order, &sc, &def);
                if (def < cur_def || (def == cur_def && sc > cur_sc + 1e-5f)) {
                    cur_def = def; cur_sc = sc; best_v = v; clock_improved = 1;
                }
            }
            q9[i] = best_v;
        }

        compute_grid(q7, q8, q9, cols);
        printf("  Stage B Result: %s (Score = %.4f | Defects = %d)\n",
               clock_improved ? "CLOCKS UPDATED" : "Clocks stationary", cur_sc, cur_def);

        if (!clock_improved && best_local_def >= cur_def) {
            printf("\nCONVERGENCE: Both Clocks and Transposition are stationary at strict local minimum.\n");
            break;
        }
    }

    printf("\n======================================================\n");
    printf("FINAL PK10 ALTERNATING DEEP SOLVER RESULT:\n");
    printf("Score: %.4f | Defects: %d / 468 (%.1f%% valid)\n",
           cur_sc, cur_def, (468 - cur_def)/468.0f * 100.0f);
    printf("Q7: ["); for(int i=0;i<7;i++) printf("%d%s", q7[i], i==6?"":", "); printf("]\n");
    printf("Q8: ["); for(int i=0;i<8;i++) printf("%d%s", q8[i], i==7?"":", "); printf("]\n");
    printf("Q9: ["); for(int i=0;i<9;i++) printf("%d%s", q9[i], i==8?"":", "); printf("]\n");
    printf("Order: [");
    for (int i = 0; i < COLS; i++) printf("%d%s", order[i], i == COLS-1 ? "" : ", ");
    printf("]\n");

    return 0;
}

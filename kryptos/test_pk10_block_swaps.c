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

    // Baseline column order:
    int base_order[COLS] = {
        29, 1, 34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16,
        20, 37, 39, 7, 31, 33, 32, 36, 22, 35, 27, 10, 9,
        41, 8, 19, 11, 18, 14, 6, 24, 5, 4, 40
    };

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

    float base_sc; int base_def;
    eval_grid_order(cols, base_order, &base_sc, &base_def);
    printf("Initial Record Baseline: Score = %.4f | Defects = %d / 468 (%.1f%% valid)\n",
           base_sc, base_def, (468 - base_def)/468.0f * 100.0f);

    float best_sc = base_sc;
    int best_def = base_def;
    int best_order[COLS];
    memcpy(best_order, base_order, sizeof(base_order));

    // Phase 1: Exhaustive Pairwise Block Swaps of equal size L
    printf("\n=== Phase 1: Exhaustive Pairwise Block Swaps (L in {2, 3, 4, 5, 6, 7, 8, 10, 14}) ===\n");
    int block_sizes[] = {2, 3, 4, 5, 6, 7, 8, 10, 14};
    int n_sizes = sizeof(block_sizes) / sizeof(block_sizes[0]);

    int swaps_tested = 0;
    for (int s_idx = 0; s_idx < n_sizes; s_idx++) {
        int L = block_sizes[s_idx];
        int top_def_for_L = 999;
        float top_sc_for_L = -999.0f;
        int best_i = -1, best_j = -1;

        for (int i = 0; i <= COLS - 2 * L; i++) {
            for (int j = i + L; j <= COLS - L; j++) {
                int test_order[COLS];
                memcpy(test_order, base_order, sizeof(base_order));

                // Swap block [i..i+L-1] with block [j..j+L-1]
                for (int k = 0; k < L; k++) {
                    int tmp = test_order[i + k];
                    test_order[i + k] = test_order[j + k];
                    test_order[j + k] = tmp;
                }

                float sc; int def;
                eval_grid_order(cols, test_order, &sc, &def);
                swaps_tested++;

                if (def < top_def_for_L || (def == top_def_for_L && sc > top_sc_for_L)) {
                    top_def_for_L = def;
                    top_sc_for_L = sc;
                    best_i = i; best_j = j;
                }

                if (def < best_def || (def == best_def && sc > best_sc)) {
                    best_def = def; best_sc = sc;
                    memcpy(best_order, test_order, sizeof(best_order));
                    printf("  >>> IMPROVEMENT: Swap L=%d at pos (%d, %d): Score = %.4f | Defects = %d / 468\n",
                           L, i, j, best_sc, best_def);
                }
            }
        }
        printf("L = %2d: Best Swap pos (%2d, %2d) -> Defects = %3d | Score = %.4f\n",
               L, best_i, best_j, top_def_for_L, top_sc_for_L);
    }
    printf("Total block swaps tested: %d\n", swaps_tested);

    // Phase 2: Exhaustive Block Inversions of size L
    printf("\n=== Phase 2: Exhaustive Block Inversions (L in {2, 3, 4, 5, 6, 7, 8, 10, 14, 21}) ===\n");
    int inv_sizes[] = {2, 3, 4, 5, 6, 7, 8, 10, 14, 21};
    int n_inv_sizes = sizeof(inv_sizes) / sizeof(inv_sizes[0]);

    for (int s_idx = 0; s_idx < n_inv_sizes; s_idx++) {
        int L = inv_sizes[s_idx];
        int top_def_for_L = 999;
        float top_sc_for_L = -999.0f;
        int best_pos = -1;

        for (int i = 0; i <= COLS - L; i++) {
            int test_order[COLS];
            memcpy(test_order, base_order, sizeof(base_order));

            // Invert block [i..i+L-1]
            for (int k = 0; k < L / 2; k++) {
                int tmp = test_order[i + k];
                test_order[i + k] = test_order[i + L - 1 - k];
                test_order[i + L - 1 - k] = tmp;
            }

            float sc; int def;
            eval_grid_order(cols, test_order, &sc, &def);

            if (def < top_def_for_L || (def == top_def_for_L && sc > top_sc_for_L)) {
                top_def_for_L = def;
                top_sc_for_L = sc;
                best_pos = i;
            }

            if (def < best_def || (def == best_def && sc > best_sc)) {
                best_def = def; best_sc = sc;
                memcpy(best_order, test_order, sizeof(best_order));
                printf("  >>> IMPROVEMENT: Inversion L=%d at pos %d: Score = %.4f | Defects = %d / 468\n",
                       L, i, best_sc, best_def);
            }
        }
        printf("L = %2d: Best Inversion at pos %2d -> Defects = %3d | Score = %.4f\n",
               L, best_pos, top_def_for_L, top_sc_for_L);
    }

    // Phase 3: Simulated Annealing with Compound Block Moves
    printf("\n=== Phase 3: Compound Block Simulated Annealing (1,000,000 steps across threads) ===\n");
    #pragma omp parallel
    {
        unsigned int seed = 4321 + omp_get_thread_num() * 19999;
        int cur_order[COLS];
        memcpy(cur_order, base_order, sizeof(base_order));
        float cur_sc = base_sc;
        int cur_def = base_def;

        int local_best_order[COLS];
        memcpy(local_best_order, base_order, sizeof(base_order));
        float local_best_sc = base_sc;
        int local_best_def = base_def;

        int steps = 500000;
        float T_start = 0.5f, T_end = 0.001f;

        for (int s = 0; s < steps; s++) {
            float frac = (float)s / steps;
            float T = T_start * powf(T_end / T_start, frac);

            int next_order[COLS];
            memcpy(next_order, cur_order, sizeof(cur_order));

            int move_type = rand_r(&seed) % 3;
            if (move_type == 0) {
                // Block swap of length L in [2, 6]
                int L = 2 + (rand_r(&seed) % 5);
                int i = rand_r(&seed) % (COLS - 2 * L + 1);
                int j = i + L + (rand_r(&seed) % (COLS - i - 2 * L + 1));
                for (int k = 0; k < L; k++) {
                    int tmp = next_order[i + k];
                    next_order[i + k] = next_order[j + k];
                    next_order[j + k] = tmp;
                }
            } else if (move_type == 1) {
                // Block inversion of length L in [2, 8]
                int L = 2 + (rand_r(&seed) % 7);
                int i = rand_r(&seed) % (COLS - L + 1);
                for (int k = 0; k < L / 2; k++) {
                    int tmp = next_order[i + k];
                    next_order[i + k] = next_order[i + L - 1 - k];
                    next_order[i + L - 1 - k] = tmp;
                }
            } else {
                // Block shift / rotation of length L in [3, 8]
                int L = 3 + (rand_r(&seed) % 6);
                int i = rand_r(&seed) % (COLS - L + 1);
                int shift = 1 + (rand_r(&seed) % (L - 1));
                int temp[10];
                for (int k = 0; k < L; k++) temp[k] = next_order[i + (k + shift) % L];
                for (int k = 0; k < L; k++) next_order[i + k] = temp[k];
            }

            float next_sc; int next_def;
            eval_grid_order(cols, next_order, &next_sc, &next_def);

            float d_fit = (cur_def - next_def) * 1.5f + (next_sc - cur_sc);
            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                memcpy(cur_order, next_order, sizeof(cur_order));
                cur_sc = next_sc;
                cur_def = next_def;

                if (cur_def < local_best_def || (cur_def == local_best_def && cur_sc > local_best_sc)) {
                    local_best_def = cur_def;
                    local_best_sc = cur_sc;
                    memcpy(local_best_order, cur_order, sizeof(cur_order));
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_def < best_def || (local_best_def == best_def && local_best_sc > best_sc)) {
                best_def = local_best_def;
                best_sc = local_best_sc;
                memcpy(best_order, local_best_order, sizeof(best_order));
                printf("[Thread %d] NEW RECORD FROM BLOCK SA: Score = %.4f | Defects = %d / 468\n",
                       omp_get_thread_num(), best_sc, best_def);
            }
        }
    }

    printf("\n======================================================\n");
    printf("FINAL BLOCK-SWAP EVALUATION RESULT:\n");
    printf("Score: %.4f | Defects: %d / 468 (%.1f%% valid)\n",
           best_sc, best_def, (468 - best_def)/468.0f * 100.0f);
    printf("Baseline Record: Score = %.4f | Defects = %d / 468 (%.1f%% valid)\n",
           base_sc, base_def, (468 - base_def)/468.0f * 100.0f);
    if (best_def < base_def) {
        printf("RESULT: BLOCK SWAP SUCCEEDED! New record established.\n");
    } else {
        printf("RESULT: RECORD IS STRICTLY STATIONARY under all block swaps, block inversions, and block rotations.\n");
    }

    return 0;
}

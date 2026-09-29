#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W 12

const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
const int s13[7] = {0, 2, 9, 10, 10, 6, 7};

float quad_table[26*26*26*26];
int alph_to_std[26];

int get_idx(char c) {
    for (int i = 0; i < 26; i++) {
        if (ALPH[i] == c) return i;
    }
    return -1;
}

void load_quads() {
    for (int i = 0; i < 26*26*26*26; i++) quad_table[i] = -8.0f;
    for (int i = 0; i < 26; i++) alph_to_std[i] = ALPH[i] - 'A';

    FILE *f = fopen("/home/user/english_quads.tsv", "r");
    if (!f) { printf("Failed to open quads\n"); exit(1); }
    char line[128];
    while (fgets(line, sizeof(line), f)) {
        char q[5];
        float sc;
        if (sscanf(line, "%4s\t%f", q, &sc) == 2) {
            int c0 = q[0] - 'A', c1 = q[1] - 'A', c2 = q[2] - 'A', c3 = q[3] - 'A';
            if (c0>=0 && c0<26 && c1>=0 && c1<26 && c2>=0 && c2<26 && c3>=0 && c3<26) {
                int code = ((c0 * 26 + c1) * 26 + c2) * 26 + c3;
                quad_table[code] = sc;
            }
        }
    }
    fclose(f);
}

// Decode Nihilist transposition on 12x12
// cipher is length 144
// takeoff: 0 = columns, 1 = rows
void decode_nihilist(const int *cipher, const int *perm, int takeoff, int *plain) {
    // invert perm
    // perm maps original index to rank
    // In decode:
    // sq3 is filled from cipher
    int sq3[W][W];
    int k = 0;
    if (takeoff == 1) { // rows
        for (int r = 0; r < W; r++) {
            for (int c = 0; c < W; c++) {
                sq3[r][c] = cipher[k++];
            }
        }
    } else { // columns
        for (int c = 0; c < W; c++) {
            for (int r = 0; r < W; r++) {
                sq3[r][c] = cipher[k++];
            }
        }
    }

    // Invert row permutation
    int sq2[W][W];
    for (int i = 0; i < W; i++) {
        int target_r = perm[i];
        for (int c = 0; c < W; c++) {
            sq2[target_r][c] = sq3[i][c];
        }
    }

    // Invert col permutation
    int grid[W][W];
    for (int r = 0; r < W; r++) {
        for (int j = 0; j < W; j++) {
            int target_c = perm[j];
            grid[r][target_c] = sq2[r][j];
        }
    }

    // Unroll grid by rows
    k = 0;
    for (int r = 0; r < W; r++) {
        for (int c = 0; c < W; c++) {
            plain[k++] = grid[r][c];
        }
    }
}

float score_text(const int *plain) {
    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        int c0 = alph_to_std[plain[i]];
        int c1 = alph_to_std[plain[i+1]];
        int c2 = alph_to_std[plain[i+2]];
        int c3 = alph_to_std[plain[i+3]];
        int code = ((c0 * 26 + c1) * 26 + c2) * 26 + c3;
        sc += quad_table[code];
    }
    return sc / (N - 3);
}

int main() {
    load_quads();
    int c_arr[N];
    for (int i = 0; i < N; i++) c_arr[i] = get_idx(CT[i]);

    printf("Starting Nihilist Transposition 12x12 Annealer across 128 parity masks...\n");

    float global_best_sc = -999.0f;
    int global_best_mask = -1;
    int global_best_perm[W];
    int global_best_takeoff = -1;

    #pragma omp parallel for schedule(dynamic, 1)
    for (int mask = 0; mask < 128; mask++) {
        int z[N];
        for (int i = 0; i < N; i++) {
            int shift = s13[i % 7] + ((mask & (1 << (i % 7))) ? 13 : 0);
            z[i] = (c_arr[i] - shift + 26) % 26;
        }

        unsigned int seed = 12345 + mask * 777;

        for (int takeoff = 0; takeoff < 2; takeoff++) {
            // Run 50 restarts of simulated annealing
            for (int restart = 0; restart < 50; restart++) {
                int perm[W];
                for (int i = 0; i < W; i++) perm[i] = i;
                // Fisher-Yates
                for (int i = W - 1; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
                }

                int plain[N];
                decode_nihilist(z, perm, takeoff, plain);
                float cur_sc = score_text(plain);
                float best_sc = cur_sc;

                float temp = 5.0f;
                float step = 0.05f;

                while (temp > 0.05f) {
                    for (int iter = 0; iter < 100; iter++) {
                        int i = rand_r(&seed) % W;
                        int j = rand_r(&seed) % W;
                        while (j == i) j = rand_r(&seed) % W;

                        int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
                        decode_nihilist(z, perm, takeoff, plain);
                        float cand_sc = score_text(plain);
                        float delta = cand_sc - cur_sc;

                        if (delta > 0 || (float)rand_r(&seed)/RAND_MAX < exp(delta / temp)) {
                            cur_sc = cand_sc;
                            if (cur_sc > best_sc) {
                                best_sc = cur_sc;
                            }
                        } else {
                            // Revert
                            tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
                        }
                    }
                    temp -= step;
                }

                #pragma omp critical
                {
                    if (best_sc > global_best_sc) {
                        global_best_sc = best_sc;
                        global_best_mask = mask;
                        global_best_takeoff = takeoff;
                        memcpy(global_best_perm, perm, sizeof(perm));
                        printf("New Best! Mask=%3d, Takeoff=%s, Score=%.4f\n", 
                               mask, takeoff ? "rows" : "cols", best_sc);
                        decode_nihilist(z, perm, takeoff, plain);
                        printf("PT: ");
                        for (int k = 0; k < 60; k++) printf("%c", ALPH[plain[k]]);
                        printf("...\n");
                    }
                }
            }
        }
    }

    printf("\nFinished Nihilist 12x12 sweep. Global Best Score: %.4f (Mask %d, Takeoff %s)\n",
           global_best_sc, global_best_mask, global_best_takeoff ? "rows" : "cols");
    return 0;
}

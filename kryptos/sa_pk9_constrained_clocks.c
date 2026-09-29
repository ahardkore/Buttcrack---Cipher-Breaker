#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int ct_std[N];
static int kr_to_std[26];
static int std_to_kr[26];
static float quad_table[26][26][26][26];

void load_models() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Missing english_quadgrams.txt\n"); exit(1); }
    char q[16]; double cnt; double total = 0;
    while (fscanf(f, "%s %lf", q, &cnt) == 2) if (strlen(q) == 4) total += cnt;
    rewind(f);
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26)
                quad_table[a][b][c][d] = (float)log10((cnt + 0.01) / total);
        }
    }
    fclose(f);

    for (int i = 0; i < 26; i++) {
        kr_to_std[i] = ALPH[i] - 'A';
        std_to_kr[ALPH[i] - 'A'] = i;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
}

static inline float score_quadgrams(const int *txt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return s / (N - 3);
}

// Build plaintext given (q4, q7, perm, mode, orientation)
// mode: 0: Kr-Vig, 1: Kr-Beau, 2: Std-Vig, 3: Std-Beau
// orient: 0: Col-readout, 1: Row-readout
static inline void build_plaintext(const int *q4, const int *q7, const int *perm, int mode, int orient, int *out) {
    int use_kr = (mode == 0 || mode == 1);
    int is_beau = (mode == 1 || mode == 3);
    const int *src_ct = use_kr ? ct_kr : ct_std;
    const int *to_std = use_kr ? kr_to_std : NULL;

    // Decrypt Z
    int Z[N];
    for (int i = 0; i < N; i++) {
        int shift = (q4[i % 4] + q7[i % 7]) % 26;
        int c_val = src_ct[i];
        int p_val = is_beau ? (shift - c_val + 26) % 26 : (c_val - shift + 26) % 26;
        Z[i] = use_kr ? to_std[p_val] : p_val;
    }

    int idx = 0;
    if (orient == 0) {
        // Col-readout: columns of Z are permuted
        for (int r = 0; r < H; r++) {
            for (int c = 0; c < W; c++) {
                out[idx++] = Z[perm[c] * H + r];
            }
        }
    } else {
        // Row-readout: rows of Z are read by permuted columns
        for (int r = 0; r < H; r++) {
            for (int c = 0; c < W; c++) {
                out[idx++] = Z[r * W + perm[c]];
            }
        }
    }
}

int main() {
    load_models();
    printf("Models loaded. Executing High-Intensity Simulated Annealing on (Q4, Q7, Permutation)...\n");

    float global_best_sc = -999.0f;
    int global_best_pt[N];
    int global_best_q4[4], global_best_q7[7], global_best_perm[W];
    int global_best_mode = 0, global_best_orient = 0;

    double t0 = omp_get_wtime();

    for (int mode = 0; mode < 4; mode++) {
        for (int orient = 0; orient < 2; orient++) {
            printf("\n--- Starting Search: Mode %d, Orientation %d ---\n", mode, orient);

            #pragma omp parallel
            {
                unsigned int seed = 54321 + omp_get_thread_num() * 19999 + mode * 1000 + orient * 100;
                float local_best_sc = -999.0f;
                int local_best_pt[N];
                int local_best_q4[4], local_best_q7[7], local_best_perm[W];

                int cur_q4[4], cur_q7[7], cur_perm[W];
                int cur_pt[N];

                for (int restart = 0; restart < 1000; restart++) {
                    // Random initialization
                    cur_q4[0] = 0;
                    for (int i = 1; i < 4; i++) cur_q4[i] = rand_r(&seed) % 26;
                    for (int i = 0; i < 7; i++) cur_q7[i] = rand_r(&seed) % 26;

                    for (int i = 0; i < W; i++) cur_perm[i] = i;
                    for (int i = W - 1; i > 0; i--) {
                        int j = rand_r(&seed) % (i + 1);
                        int t = cur_perm[i]; cur_perm[i] = cur_perm[j]; cur_perm[j] = t;
                    }

                    build_plaintext(cur_q4, cur_q7, cur_perm, mode, orient, cur_pt);
                    float cur_sc = score_quadgrams(cur_pt);

                    float T = 1.5f;
                    float T_min = 0.01f;
                    float alpha = 0.9995f;

                    for (int step = 0; step < 8000; step++) {
                        int next_q4[4], next_q7[7], next_perm[W];
                        memcpy(next_q4, cur_q4, sizeof(cur_q4));
                        memcpy(next_q7, cur_q7, sizeof(cur_q7));
                        memcpy(next_perm, cur_perm, sizeof(next_perm));

                        int mut = rand_r(&seed) % 100;
                        if (mut < 35) {
                            // Swap two columns in perm
                            int a = rand_r(&seed) % W;
                            int b = rand_r(&seed) % W;
                            int t = next_perm[a]; next_perm[a] = next_perm[b]; next_perm[b] = t;
                        } else if (mut < 50) {
                            // Rotate a slice of columns
                            int a = rand_r(&seed) % W;
                            int b = rand_r(&seed) % W;
                            if (a > b) { int t = a; a = b; b = t; }
                            int first = next_perm[a];
                            for (int k = a; k < b; k++) next_perm[k] = next_perm[k+1];
                            next_perm[b] = first;
                        } else if (mut < 70) {
                            // Mutate Q4
                            int idx = 1 + rand_r(&seed) % 3;
                            int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                            next_q4[idx] = (next_q4[idx] + delta) % 26;
                        } else {
                            // Mutate Q7
                            int idx = rand_r(&seed) % 7;
                            int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                            next_q7[idx] = (next_q7[idx] + delta) % 26;
                        }

                        int next_pt[N];
                        build_plaintext(next_q4, next_q7, next_perm, mode, orient, next_pt);
                        float next_sc = score_quadgrams(next_pt);

                        float diff = next_sc - cur_sc;
                        if (diff > 0.0f || expf(diff / T) > ((float)rand_r(&seed) / RAND_MAX)) {
                            cur_sc = next_sc;
                            memcpy(cur_q4, next_q4, sizeof(cur_q4));
                            memcpy(cur_q7, next_q7, sizeof(cur_q7));
                            memcpy(cur_perm, next_perm, sizeof(cur_perm));

                            if (cur_sc > local_best_sc) {
                                local_best_sc = cur_sc;
                                memcpy(local_best_pt, cur_pt, sizeof(cur_pt));
                                memcpy(local_best_q4, cur_q4, sizeof(cur_q4));
                                memcpy(local_best_q7, cur_q7, sizeof(cur_q7));
                                memcpy(local_best_perm, cur_perm, sizeof(cur_perm));
                            }
                        }

                        T *= alpha;
                        if (T < T_min) T = T_min;
                    }
                }

                #pragma omp critical
                {
                    if (local_best_sc > global_best_sc) {
                        global_best_sc = local_best_sc;
                        memcpy(global_best_pt, local_best_pt, sizeof(global_best_pt));
                        memcpy(global_best_q4, local_best_q4, sizeof(global_best_q4));
                        memcpy(global_best_q7, local_best_q7, sizeof(global_best_q7));
                        memcpy(global_best_perm, local_best_perm, sizeof(global_best_perm));
                        global_best_mode = mode;
                        global_best_orient = orient;

                        char pt_str[N+1];
                        for (int i = 0; i < N; i++) pt_str[i] = global_best_pt[i] + 'A';
                        pt_str[N] = '\0';

                        printf(">>> [Thread %d] NEW BEST SCORE: %.4f | Mode %d, Orient %d <<<\n",
                               omp_get_thread_num(), global_best_sc, global_best_mode, global_best_orient);
                        printf("q4: [%d, %d, %d, %d]\n", global_best_q4[0], global_best_q4[1], global_best_q4[2], global_best_q4[3]);
                        printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n", global_best_q7[0], global_best_q7[1], global_best_q7[2], global_best_q7[3], global_best_q7[4], global_best_q7[5], global_best_q7[6]);
                        printf("perm: [");
                        for (int i = 0; i < W; i++) printf("%d%s", global_best_perm[i], i==W-1?"":", ");
                        printf("]\n");
                        printf("PT: %.100s\n\n", pt_str);
                    }
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nSearch finished in %.2f seconds.\n", elapsed);
    printf("Global Best Score: %.4f | Mode %d, Orient %d\n", global_best_sc, global_best_mode, global_best_orient);
    char final_pt[N+1];
    for (int i = 0; i < N; i++) final_pt[i] = global_best_pt[i] + 'A';
    final_pt[N] = '\0';
    printf("Plaintext:\n%s\n", final_pt);

    return 0;
}

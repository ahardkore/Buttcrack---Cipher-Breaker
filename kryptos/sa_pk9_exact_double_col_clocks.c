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
    if (!f) exit(1);
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

static inline void col_decrypt_grid(const int *in, const int *order, int *out) {
    int grid[H][W];
    int idx = 0;
    for (int c_idx = 0; c_idx < W; c_idx++) {
        int col = order[c_idx];
        for (int r = 0; r < H; r++) grid[r][col] = in[idx++];
    }
    idx = 0;
    for (int r = 0; r < H; r++)
        for (int c = 0; c < W; c++) out[idx++] = grid[r][c];
}

static inline float score_quadgrams(const int *txt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return s / (N - 3);
}

static inline void evaluate_state(const int *q4, const int *q7, const int *o1, const int *o2, int mode, float *score_out, int *pt_out) {
    // Mode 1: Kr-Beaufort, Mode 0: Kr-Vigenere, Mode 3: Std-Beaufort, Mode 2: Std-Vigenere
    int use_kr = (mode == 0 || mode == 1);
    int is_beau = (mode == 1 || mode == 3);
    const int *src_ct = use_kr ? ct_kr : ct_std;
    const int *to_std = use_kr ? kr_to_std : NULL;

    // Decrypt substitution on ciphertext positions: Z2[i] = decrypt(CT[i], K[i % 28])
    int Z2[N];
    for (int i = 0; i < N; i++) {
        int shift = (q4[i % 4] + q7[i % 7]) % 26;
        int c_val = src_ct[i];
        int p_val = is_beau ? (shift - c_val + 26) % 26 : (c_val - shift + 26) % 26;
        Z2[i] = use_kr ? to_std[p_val] : p_val;
    }

    // Decrypt Stage 2: Z1 = DecCol(Z2, o2)
    int Z1[N];
    col_decrypt_grid(Z2, o2, Z1);

    // Decrypt Stage 1: PT = DecCol(Z1, o1)
    col_decrypt_grid(Z1, o1, pt_out);

    *score_out = score_quadgrams(pt_out);
}

void keyword_to_order(const char *kw, int *order, int len) {
    int used[32] = {0}, count = 0;
    for (int c = 'A'; c <= 'Z'; c++) {
        for (int i = 0; i < len; i++) {
            if (kw[i] == c && !used[i]) { order[count++] = i; used[i] = 1; }
        }
    }
}

int main() {
    load_models();
    printf("Models loaded. Executing Exact Joint SA on (Q4, Q7, O1, O2)...\n");

    int needle_order[W], gold_order[W], metal_order[W], thread_order[W];
    keyword_to_order("NEEDLEMAKING", needle_order, W);
    keyword_to_order("GOLDSMITHING", gold_order, W);
    keyword_to_order("METALWORKING", metal_order, W);
    keyword_to_order("THREADMAKING", thread_order, W);

    float global_best_sc = -999.0f;
    int global_best_q4[4], global_best_q7[7], global_best_o1[W], global_best_o2[W];
    int global_best_pt[N];
    int global_best_mode = 1;

    double t0 = omp_get_wtime();

    // Focus on Mode 1 (Kr-Beaufort) and Mode 0 (Kr-Vigenere)
    for (int mode_idx = 0; mode_idx < 2; mode_idx++) {
        int mode = (mode_idx == 0) ? 1 : 0;
        printf("\n=== Commencing Search for Mode %d (%s) ===\n", mode, (mode == 1) ? "Kryptos Beaufort" : "Kryptos Vigenere");

        #pragma omp parallel
        {
            unsigned int seed = 44444 + omp_get_thread_num() * 11111 + mode * 777;
            float local_best_sc = -999.0f;
            int local_best_q4[4], local_best_q7[7], local_best_o1[W], local_best_o2[W];
            int local_best_pt[N];

            int cur_q4[4], cur_q7[7], cur_o1[W], cur_o2[W];
            int cur_pt[N];

            for (int restart = 0; restart < 500; restart++) {
                // Initialize
                cur_q4[0] = 0;
                for (int i = 1; i < 4; i++) cur_q4[i] = rand_r(&seed) % 26;
                for (int i = 0; i < 7; i++) cur_q7[i] = rand_r(&seed) % 26;

                int seed_type = restart % 5;
                if (seed_type == 0) {
                    memcpy(cur_o1, needle_order, sizeof(cur_o1));
                    memcpy(cur_o2, gold_order, sizeof(cur_o2));
                } else if (seed_type == 1) {
                    memcpy(cur_o1, gold_order, sizeof(cur_o1));
                    memcpy(cur_o2, needle_order, sizeof(cur_o2));
                } else if (seed_type == 2) {
                    memcpy(cur_o1, metal_order, sizeof(cur_o1));
                    memcpy(cur_o2, thread_order, sizeof(cur_o2));
                } else if (seed_type == 3) {
                    memcpy(cur_o1, thread_order, sizeof(cur_o1));
                    memcpy(cur_o2, metal_order, sizeof(cur_o2));
                } else {
                    for (int i = 0; i < W; i++) { cur_o1[i] = i; cur_o2[i] = i; }
                    for (int i = W - 1; i > 0; i--) {
                        int j1 = rand_r(&seed) % (i + 1);
                        int t1 = cur_o1[i]; cur_o1[i] = cur_o1[j1]; cur_o1[j1] = t1;
                        int j2 = rand_r(&seed) % (i + 1);
                        int t2 = cur_o2[i]; cur_o2[i] = cur_o2[j2]; cur_o2[j2] = t2;
                    }
                }

                float cur_sc;
                evaluate_state(cur_q4, cur_q7, cur_o1, cur_o2, mode, &cur_sc, cur_pt);

                float T = 1.2f;
                float T_min = 0.005f;
                float alpha = 0.9997f;

                for (int step = 0; step < 15000; step++) {
                    int next_q4[4], next_q7[7], next_o1[W], next_o2[W];
                    memcpy(next_q4, cur_q4, sizeof(cur_q4));
                    memcpy(next_q7, cur_q7, sizeof(cur_q7));
                    memcpy(next_o1, cur_o1, sizeof(cur_o1));
                    memcpy(next_o2, cur_o2, sizeof(cur_o2));

                    int mut = rand_r(&seed) % 100;
                    if (mut < 30) {
                        // Mutate o1 (swap 2 columns)
                        int a = rand_r(&seed) % W;
                        int b = rand_r(&seed) % W;
                        int t = next_o1[a]; next_o1[a] = next_o1[b]; next_o1[b] = t;
                    } else if (mut < 60) {
                        // Mutate o2 (swap 2 columns)
                        int a = rand_r(&seed) % W;
                        int b = rand_r(&seed) % W;
                        int t = next_o2[a]; next_o2[a] = next_o2[b]; next_o2[b] = t;
                    } else if (mut < 80) {
                        // Mutate Q7
                        int idx = rand_r(&seed) % 7;
                        int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                        next_q7[idx] = (next_q7[idx] + delta) % 26;
                    } else {
                        // Mutate Q4
                        int idx = 1 + (rand_r(&seed) % 3);
                        int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                        next_q4[idx] = (next_q4[idx] + delta) % 26;
                    }

                    int next_pt[N];
                    float next_sc;
                    evaluate_state(next_q4, next_q7, next_o1, next_o2, mode, &next_sc, next_pt);

                    float diff = next_sc - cur_sc;
                    if (diff > 0.0f || expf(diff / T) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = next_sc;
                        memcpy(cur_q4, next_q4, sizeof(cur_q4));
                        memcpy(cur_q7, next_q7, sizeof(cur_q7));
                        memcpy(cur_o1, next_o1, sizeof(cur_o1));
                        memcpy(cur_o2, next_o2, sizeof(cur_o2));
                        memcpy(cur_pt, next_pt, sizeof(cur_pt));

                        if (cur_sc > local_best_sc) {
                            local_best_sc = cur_sc;
                            memcpy(local_best_q4, cur_q4, sizeof(cur_q4));
                            memcpy(local_best_q7, cur_q7, sizeof(cur_q7));
                            memcpy(local_best_o1, cur_o1, sizeof(cur_o1));
                            memcpy(local_best_o2, cur_o2, sizeof(cur_o2));
                            memcpy(local_best_pt, cur_pt, sizeof(cur_pt));
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
                    memcpy(global_best_q4, local_best_q4, sizeof(global_best_q4));
                    memcpy(global_best_q7, local_best_q7, sizeof(global_best_q7));
                    memcpy(global_best_o1, local_best_o1, sizeof(global_best_o1));
                    memcpy(global_best_o2, local_best_o2, sizeof(global_best_o2));
                    memcpy(global_best_pt, local_best_pt, sizeof(global_best_pt));
                    global_best_mode = mode;

                    char pt_str[N+1];
                    for (int i = 0; i < N; i++) pt_str[i] = global_best_pt[i] + 'A';
                    pt_str[N] = '\0';

                    printf("\n>>> [Thread %d] NEW BEST SCORE: %.4f (Mode %d) <<<\n",
                           omp_get_thread_num(), global_best_sc, global_best_mode);
                    printf("  q4: [%d, %d, %d, %d]\n", global_best_q4[0], global_best_q4[1], global_best_q4[2], global_best_q4[3]);
                    printf("  q7: [%d, %d, %d, %d, %d, %d, %d]\n", global_best_q7[0], global_best_q7[1], global_best_q7[2], global_best_q7[3], global_best_q7[4], global_best_q7[5], global_best_q7[6]);
                    printf("  o1: [");
                    for (int i = 0; i < W; i++) printf("%d%s", global_best_o1[i], i==W-1?"":", ");
                    printf("]\n");
                    printf("  o2: [");
                    for (int i = 0; i < W; i++) printf("%d%s", global_best_o2[i], i==W-1?"":", ");
                    printf("]\n");
                    printf("  PT: %.100s\n", pt_str);
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nExecution finished in %.2f seconds.\n", elapsed);
    printf("Final Best Score: %.4f | Mode %d\n", global_best_sc, global_best_mode);
    char final_pt[N+1];
    for (int i = 0; i < N; i++) final_pt[i] = global_best_pt[i] + 'A';
    final_pt[N] = '\0';
    printf("Plaintext:\n%s\n", final_pt);

    return 0;
}

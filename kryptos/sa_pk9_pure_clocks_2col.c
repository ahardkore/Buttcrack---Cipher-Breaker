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

    for (int a = 0; a < 26; a++) {
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
    }
}

void col_decrypt(const int *in, const int *order, int *out, int w, int h) {
    int grid[H][W];
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = order[c_idx];
        for (int r = 0; r < h; r++) grid[r][col] = in[idx++];
    }
    idx = 0;
    for (int r = 0; r < h; r++)
        for (int c = 0; c < w; c++) out[idx++] = grid[r][c];
}

static inline float score_quadgrams(const int *txt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return s / (N - 3);
}

static inline void get_mapping(const int *o1, const int *o2, int *pt_to_z2) {
    int identity[N]; for (int j = 0; j < N; j++) identity[j] = j;
    int after2[N];
    col_decrypt(identity, o2, after2, W, H);
    col_decrypt(after2, o1, pt_to_z2, W, H);
}

// Decrypt with pure (q4, q7) clocks in Kryptos Beaufort mode:
// PT[t] = (K[pos % 28] - CT[pos]) % 26
static inline void decrypt_q4_q7(const int *pt_to_z2, const int *q4, const int *q7, int *pt) {
    for (int t = 0; t < N; t++) {
        int pos = pt_to_z2[t];
        int shift = (q4[pos % 4] + q7[pos % 7]) % 26;
        int c_val = ct_kr[pos];
        int p_val = (shift - c_val + 26) % 26;
        pt[t] = kr_to_std[p_val];
    }
}

// Polish (q4, q7) via coordinate descent
float polish_clocks(const int *pt_to_z2, int *q4, int *q7, int *pt) {
    decrypt_q4_q7(pt_to_z2, q4, q7, pt);
    float cur_sc = score_quadgrams(pt);

    int improved = 1;
    int passes = 0;
    while (improved && passes < 3) {
        improved = 0;
        passes++;

        // Polish q7[0..6]
        for (int j = 0; j < 7; j++) {
            int orig_val = q7[j];
            int best_val = orig_val;
            float best_sc = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == orig_val) continue;
                q7[j] = v;
                int test_pt[N];
                decrypt_q4_q7(pt_to_z2, q4, q7, test_pt);
                float sc = score_quadgrams(test_pt);
                if (sc > best_sc) {
                    best_sc = sc;
                    best_val = v;
                }
            }
            if (best_val != orig_val) {
                q7[j] = best_val;
                cur_sc = best_sc;
                improved = 1;
            } else {
                q7[j] = orig_val;
            }
        }

        // Polish q4[1..3]
        for (int j = 1; j < 4; j++) {
            int orig_val = q4[j];
            int best_val = orig_val;
            float best_sc = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == orig_val) continue;
                q4[j] = v;
                int test_pt[N];
                decrypt_q4_q7(pt_to_z2, q4, q7, test_pt);
                float sc = score_quadgrams(test_pt);
                if (sc > best_sc) {
                    best_sc = sc;
                    best_val = v;
                }
            }
            if (best_val != orig_val) {
                q4[j] = best_val;
                cur_sc = best_sc;
                improved = 1;
            } else {
                q4[j] = orig_val;
            }
        }
    }

    decrypt_q4_q7(pt_to_z2, q4, q7, pt);
    return cur_sc;
}

static inline void mutate_perm(int *p, unsigned int *seed) {
    int r = rand_r(seed) % 100;
    if (r < 40) {
        int a = rand_r(seed) % W, b = rand_r(seed) % W;
        int t = p[a]; p[a] = p[b]; p[b] = t;
    } else if (r < 75) {
        int a = rand_r(seed) % W, b = rand_r(seed) % W;
        if (a > b) { int t = a; a = b; b = t; }
        while (a < b) { int t = p[a]; p[a] = p[b]; p[b] = t; a++; b--; }
    } else {
        int a = rand_r(seed) % W, b = rand_r(seed) % W;
        int val = p[a];
        if (a < b) { for (int k = a; k < b; k++) p[k] = p[k+1]; }
        else { for (int k = a; k > b; k--) p[k] = p[k-1]; }
        p[b] = val;
    }
}

int main() {
    load_models();
    printf("Models loaded. Executing Pure-Clock (Q4, Q7) Double Columnar Engine on PK9...\n");

    int base_o1[W] = {3, 4, 11, 10, 6, 1, 8, 7, 9, 0, 5, 2};
    int base_o2[W] = {10, 9, 11, 2, 6, 4, 3, 1, 7, 5, 0, 8};
    int base_q4[4] = {0, 9, 13, 2};
    int base_q7[7] = {21, 18, 19, 19, 16, 0, 3};

    float global_best_sc = -999.0f;
    int global_best_o1[W], global_best_o2[W], global_best_q4[4], global_best_q7[7];
    int global_best_pt[N];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 123456 + omp_get_thread_num() * 77777;
        float local_best_sc = -999.0f;
        int local_best_o1[W], local_best_o2[W], local_best_q4[4], local_best_q7[7];
        int local_best_pt[N];

        int cur_o1[W], cur_o2[W], cur_q4[4], cur_q7[7];
        int cur_pt_to_z2[N], cur_pt[N];

        for (int restart = 0; restart < 100; restart++) {
            if (restart % 2 == 0) {
                memcpy(cur_o1, base_o1, sizeof(cur_o1));
                memcpy(cur_o2, base_o2, sizeof(cur_o2));
                memcpy(cur_q4, base_q4, sizeof(cur_q4));
                memcpy(cur_q7, base_q7, sizeof(cur_q7));
                for (int j = 0; j < (restart % 4); j++) {
                    mutate_perm(cur_o1, &seed);
                    mutate_perm(cur_o2, &seed);
                }
            } else {
                for (int i = 0; i < W; i++) { cur_o1[i] = i; cur_o2[i] = i; }
                for (int i = W - 1; i > 0; i--) {
                    int j1 = rand_r(&seed) % (i + 1); int t1 = cur_o1[i]; cur_o1[i] = cur_o1[j1]; cur_o1[j1] = t1;
                    int j2 = rand_r(&seed) % (i + 1); int t2 = cur_o2[i]; cur_o2[i] = cur_o2[j2]; cur_o2[j2] = t2;
                }
                cur_q4[0] = 0; for (int i = 1; i < 4; i++) cur_q4[i] = rand_r(&seed) % 26;
                for (int i = 0; i < 7; i++) cur_q7[i] = rand_r(&seed) % 26;
            }

            get_mapping(cur_o1, cur_o2, cur_pt_to_z2);
            float cur_sc = polish_clocks(cur_pt_to_z2, cur_q4, cur_q7, cur_pt);

            float T = 0.4f;
            float T_min = 0.005f;
            float alpha = 0.999f;

            for (int step = 0; step < 1000; step++) {
                int next_o1[W], next_o2[W], next_q4[4], next_q7[7];
                memcpy(next_o1, cur_o1, sizeof(next_o1));
                memcpy(next_o2, cur_o2, sizeof(next_o2));
                memcpy(next_q4, cur_q4, sizeof(next_q4));
                memcpy(next_q7, cur_q7, sizeof(next_q7));

                if (rand_r(&seed) % 2 == 0) {
                    mutate_perm(next_o1, &seed);
                } else {
                    mutate_perm(next_o2, &seed);
                }

                int next_pt_to_z2[N], next_pt[N];
                get_mapping(next_o1, next_o2, next_pt_to_z2);
                float next_sc = polish_clocks(next_pt_to_z2, next_q4, next_q7, next_pt);

                float diff = next_sc - cur_sc;
                if (diff > 0.0f || expf(diff / T) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = next_sc;
                    memcpy(cur_o1, next_o1, sizeof(cur_o1));
                    memcpy(cur_o2, next_o2, sizeof(cur_o2));
                    memcpy(cur_q4, next_q4, sizeof(cur_q4));
                    memcpy(cur_q7, next_q7, sizeof(cur_q7));
                    memcpy(cur_pt_to_z2, next_pt_to_z2, sizeof(cur_pt_to_z2));
                    memcpy(cur_pt, next_pt, sizeof(cur_pt));

                    if (cur_sc > local_best_sc) {
                        local_best_sc = cur_sc;
                        memcpy(local_best_o1, cur_o1, sizeof(cur_o1));
                        memcpy(local_best_o2, cur_o2, sizeof(cur_o2));
                        memcpy(local_best_q4, cur_q4, sizeof(cur_q4));
                        memcpy(local_best_q7, cur_q7, sizeof(cur_q7));
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
                memcpy(global_best_o1, local_best_o1, sizeof(global_best_o1));
                memcpy(global_best_o2, local_best_o2, sizeof(global_best_o2));
                memcpy(global_best_q4, local_best_q4, sizeof(global_best_q4));
                memcpy(global_best_q7, local_best_q7, sizeof(global_best_q7));
                memcpy(global_best_pt, local_best_pt, sizeof(global_best_pt));

                char pt_str[N+1];
                for (int i = 0; i < N; i++) pt_str[i] = global_best_pt[i] + 'A';
                pt_str[N] = '\0';

                printf("\n>>> [Thread %d] PURE-CLOCK HIGH SCORE: %.4f <<<\n",
                       omp_get_thread_num(), global_best_sc);
                printf("  q4: [%d, %d, %d, %d]\n", global_best_q4[0], global_best_q4[1], global_best_q4[2], global_best_q4[3]);
                printf("  q7: [%d, %d, %d, %d, %d, %d, %d]\n", global_best_q7[0], global_best_q7[1], global_best_q7[2], global_best_q7[3], global_best_q7[4], global_best_q7[5], global_best_q7[6]);
                printf("  o1: ["); for (int i = 0; i < W; i++) printf("%d%s", global_best_o1[i], i==W-1?"":", "); printf("]\n");
                printf("  o2: ["); for (int i = 0; i < W; i++) printf("%d%s", global_best_o2[i], i==W-1?"":", "); printf("]\n");
                printf("  PT: %.120s\n", pt_str);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nExecution finished in %.2f seconds.\n", elapsed);
    printf("FINAL PURE CLOCK BEST SCORE: %.4f\n", global_best_sc);
    char final_pt[N+1];
    for (int i = 0; i < N; i++) final_pt[i] = global_best_pt[i] + 'A';
    final_pt[N] = '\0';
    printf("Plaintext:\n%s\n", final_pt);

    return 0;
}

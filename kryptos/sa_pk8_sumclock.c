#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <omp.h>
#include <time.h>

#define N 153
static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static float quad_table[26][26][26][26];
static int ct_idx[N];
static int k_to_std[26];

void load_quads() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Cannot open quadgram file!\n"); exit(1); }
    char q[16]; float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26)
                quad_table[a][b][c][d] = sc;
        }
    }
    fclose(f);

    for (int i = 0; i < 26; i++) {
        k_to_std[i] = ALPH[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        const char *p = strchr(ALPH, CT[i]);
        ct_idx[i] = p ? (int)(p - ALPH) : 0;
    }
}

static inline uint32_t xorshift32(uint32_t *state) {
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    load_quads();

    printf("Loaded quads and initialized PK8. Starting OpenMP SA on 19 variables...\n");

    float global_best_sc = -999.0f;
    int global_best_q4[4], global_best_q5[5], global_best_q6[6], global_best_q7[7];
    char global_best_pt[N+1];

    #pragma omp parallel
    {
        uint32_t rng = 1337 + omp_get_thread_num() * 10007;
        int local_q4[4], local_q5[5], local_q6[6], local_q7[7];
        int pt[N];

        for (int restart = 0; restart < 1000; restart++) {
            // Random initialization with gauge fixing
            local_q4[0] = 0;
            for (int i = 1; i < 4; i++) local_q4[i] = xorshift32(&rng) % 26;
            local_q5[0] = 0;
            for (int i = 1; i < 5; i++) local_q5[i] = xorshift32(&rng) % 26;
            local_q6[0] = 0;
            for (int i = 1; i < 6; i++) local_q6[i] = xorshift32(&rng) % 26;
            for (int i = 0; i < 7; i++) local_q7[i] = xorshift32(&rng) % 26;

            for (int i = 0; i < N; i++) {
                int k = (local_q4[i % 4] + local_q5[i % 5] + local_q6[i % 6] + local_q7[i % 7]) % 26;
                int p_idx = (ct_idx[i] - k + 26) % 26;
                pt[i] = k_to_std[p_idx];
            }
            float cur_sc = score_plain(pt);
            float best_local_sc = cur_sc;

            float temp = 0.5f;
            float cooling = 0.9995f;

            for (int step = 0; step < 15000; step++) {
                // Pick a random variable to perturb
                int var_idx = xorshift32(&rng) % 19;
                int old_val;
                int *ptr;
                int p_mod;

                if (var_idx < 3) {
                    ptr = &local_q4[var_idx + 1];
                    p_mod = 4;
                } else if (var_idx < 7) {
                    ptr = &local_q5[var_idx - 3 + 1];
                    p_mod = 5;
                } else if (var_idx < 12) {
                    ptr = &local_q6[var_idx - 7 + 1];
                    p_mod = 6;
                } else {
                    ptr = &local_q7[var_idx - 12];
                    p_mod = 7;
                }

                old_val = *ptr;
                int new_val = (old_val + 1 + (xorshift32(&rng) % 25)) % 26;
                *ptr = new_val;

                // Re-decrypt affected positions
                // Actually, full re-decrypt of 153 chars takes only 150 cycles!
                for (int i = 0; i < N; i++) {
                    int k = (local_q4[i % 4] + local_q5[i % 5] + local_q6[i % 6] + local_q7[i % 7]) % 26;
                    int p_idx = (ct_idx[i] - k + 26) % 26;
                    pt[i] = k_to_std[p_idx];
                }
                float new_sc = score_plain(pt);

                if (new_sc > cur_sc || (float)(xorshift32(&rng) & 0xFFFFFF)/0x1000000 < expf((new_sc - cur_sc) / temp)) {
                    cur_sc = new_sc;
                    if (cur_sc > best_local_sc) {
                        best_local_sc = cur_sc;
                    }
                } else {
                    *ptr = old_val;
                }
                temp *= cooling;
            }

            if (best_local_sc > -8.5f) {
                #pragma omp critical
                {
                    if (best_local_sc > global_best_sc) {
                        global_best_sc = best_local_sc;
                        memcpy(global_best_q4, local_q4, sizeof(local_q4));
                        memcpy(global_best_q5, local_q5, sizeof(local_q5));
                        memcpy(global_best_q6, local_q6, sizeof(local_q6));
                        memcpy(global_best_q7, local_q7, sizeof(local_q7));
                        for (int i = 0; i < N; i++) {
                            int k = (local_q4[i % 4] + local_q5[i % 5] + local_q6[i % 6] + local_q7[i % 7]) % 26;
                            int p_idx = (ct_idx[i] - k + 26) % 26;
                            global_best_pt[i] = 'A' + k_to_std[p_idx];
                        }
                        global_best_pt[N] = '\0';
                        printf("[NEW BEST] sc=%.4f (restart %d, thread %d)\nPT: %s\n",
                               global_best_sc, restart, omp_get_thread_num(), global_best_pt);
                    }
                }
            }
        }
    }

    printf("Search complete. Global best score: %.4f\nPT: %s\n", global_best_sc, global_best_pt);
    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 153

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static float qtable[26][26][26][26];
static char valid_q[26][26][26][26];
static float unigram_logp[26];

static const float standard_unigrams[26] = {
    0.08167f, 0.01492f, 0.02782f, 0.04253f, 0.12702f, 0.02228f, 0.02015f,
    0.06094f, 0.06966f, 0.00153f, 0.00772f, 0.04025f, 0.02406f, 0.06749f,
    0.07507f, 0.01929f, 0.00095f, 0.05987f, 0.06327f, 0.09056f, 0.02758f,
    0.00978f, 0.02360f, 0.00150f, 0.01974f, 0.00074f
};

static void load_tables(void) {
    for (int i = 0; i < 26; i++) unigram_logp[i] = logf(standard_unigrams[i]);

    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    qtable[a][b][c][d] = -9.5f;
                    valid_q[a][b][c][d] = 0;
                }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) return;
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

static inline void eval_clocks(const int ct_kr[N], const int q4[4], const int q5[5], const int q6[6], const int q7[7],
                               float *out_sc, int *out_def, float *out_ioc, int *out_rare) {
    char pt[N];
    int counts[26] = {0};
    for (int i = 0; i < N; i++) {
        int shift = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
        int p_idx = (ct_kr[i] - shift + 26) % 26;
        char ch = KRYPTOS[p_idx];
        pt[i] = ch;
        counts[ch - 'A']++;
    }

    int sum_pairs = 0;
    for (int i = 0; i < 26; i++) sum_pairs += counts[i] * (counts[i] - 1);
    *out_ioc = (float)sum_pairs / (float)(N * (N - 1));
    *out_rare = counts['J'-'A'] + counts['Q'-'A'] + counts['X'-'A'] + counts['Z'-'A'];

    float sc = 0.0f;
    int def = 0;
    for (int i = 0; i < N - 3; i++) {
        int a = pt[i] - 'A', b = pt[i+1] - 'A', c = pt[i+2] - 'A', d = pt[i+3] - 'A';
        sc += qtable[a][b][c][d];
        if (!valid_q[a][b][c][d]) def++;
    }
    *out_sc = sc / (float)(N - 3);
    *out_def = def;
}

int main(void) {
    load_tables();

    int ct_kr[N];
    for (int i = 0; i < N; i++) ct_kr[i] = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;

    // Base Q7 from PK10 / Parity Lock: [0, 9, 5, 17, 10, 2, 24]
    int base_q7[7] = {0, 9, 5, 17, 10, 2, 24};

    // Candidate Q4 from PK9: [0, 23, 11, 11]
    int base_q4[4] = {0, 23, 11, 11};

    printf("======================================================================\n");
    printf("ANNEALING CLOCKS (Q5, Q6) ON PK8 GIVEN IMPORTED Q7 & Q4\n");
    printf("======================================================================\n");

    float global_best_sc = -999.0f;
    int global_best_def = 999;
    int best_q4[4], best_q5[5], best_q6[6], best_q7[7];
    char best_pt[N + 1];

    int num_threads = omp_get_max_threads();
    printf("Running on %d OpenMP threads...\n", num_threads);

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 31337;

        for (int q7_rot = 0; q7_rot < 7; q7_rot++) {
            int local_q7[7];
            for (int k = 0; k < 7; k++) local_q7[k] = base_q7[(k + q7_rot) % 7];

            for (int q4_cand = 0; q4_cand < 4; q4_cand++) {
                int local_q4[4];
                if (q4_cand == 0) {
                    local_q4[0] = 0; local_q4[1] = 23; local_q4[2] = 11; local_q4[3] = 11;
                } else if (q4_cand == 1) {
                    local_q4[0] = 0; local_q4[1] = 0; local_q4[2] = 0; local_q4[3] = 0;
                } else if (q4_cand == 2) {
                    local_q4[0] = 0; local_q4[1] = 6; local_q4[2] = 13; local_q4[3] = 20;
                } else {
                    local_q4[0] = 0; local_q4[1] = 13; local_q4[2] = 0; local_q4[3] = 13;
                }

                // Random initialize Q5 (5 params) and Q6 (6 params)
                int local_q5[5], local_q6[6];
                for (int k = 0; k < 5; k++) local_q5[k] = rand_r(&seed) % 26;
                for (int k = 0; k < 6; k++) local_q6[k] = rand_r(&seed) % 26;

                float cur_sc, cur_ioc; int cur_def, cur_rare;
                eval_clocks(ct_kr, local_q4, local_q5, local_q6, local_q7, &cur_sc, &cur_def, &cur_ioc, &cur_rare);

                int steps = 150000;
                float T_start = 0.5f, T_end = 0.001f;

                for (int s = 0; s < steps; s++) {
                    float frac = (float)s / steps;
                    float T = T_start * powf(T_end / T_start, frac);

                    int next_q5[5], next_q6[6];
                    memcpy(next_q5, local_q5, sizeof(local_q5));
                    memcpy(next_q6, local_q6, sizeof(local_q6));

                    int m = rand_r(&seed) % 2;
                    if (m == 0) {
                        next_q5[rand_r(&seed) % 5] = rand_r(&seed) % 26;
                    } else {
                        next_q6[rand_r(&seed) % 6] = rand_r(&seed) % 26;
                    }

                    float next_sc, next_ioc; int next_def, next_rare;
                    eval_clocks(ct_kr, local_q4, next_q5, next_q6, local_q7, &next_sc, &next_def, &next_ioc, &next_rare);

                    float d_fit = (cur_def - next_def) * 1.5f + (next_sc - cur_sc);
                    if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                        memcpy(local_q5, next_q5, sizeof(local_q5));
                        memcpy(local_q6, next_q6, sizeof(local_q6));
                        cur_sc = next_sc; cur_def = next_def; cur_ioc = next_ioc; cur_rare = next_rare;

                        #pragma omp critical
                        {
                            if (cur_def < global_best_def || (cur_def == global_best_def && cur_sc > global_best_sc)) {
                                global_best_def = cur_def;
                                global_best_sc = cur_sc;
                                memcpy(best_q4, local_q4, sizeof(local_q4));
                                memcpy(best_q5, local_q5, sizeof(local_q5));
                                memcpy(best_q6, local_q6, sizeof(local_q6));
                                memcpy(best_q7, local_q7, sizeof(local_q7));
                                for (int i = 0; i < N; i++) {
                                    int shift = (best_q4[i%4] + best_q5[i%5] + best_q6[i%6] + best_q7[i%7]) % 26;
                                    best_pt[i] = KRYPTOS[(ct_kr[i] - shift + 26) % 26];
                                }
                                best_pt[N] = '\0';
                                printf("[Thread %d] NEW BEST PK8: Score = %.4f | Defects = %d / 150 (%.1f%% valid) | IoC = %.5f | Rare = %d\n",
                                       omp_get_thread_num(), global_best_sc, global_best_def,
                                       (150 - global_best_def)/150.0f * 100.0f, cur_ioc, cur_rare);
                                printf("  PT Sample: %s\n", best_pt);
                            }
                        }
                    }
                }
            }
        }
    }

    printf("\n======================================================\n");
    printf("FINAL PK8 SOLVER RESULT:\n");
    printf("Score: %.4f | Defects: %d / 150 (%.1f%% valid)\n",
           global_best_sc, global_best_def, (150 - global_best_def)/150.0f * 100.0f);
    printf("Full Plaintext:\n%s\n", best_pt);
    printf("Q4: ["); for(int i=0;i<4;i++) printf("%d%s", best_q4[i], i==3?"":", "); printf("]\n");
    printf("Q5: ["); for(int i=0;i<5;i++) printf("%d%s", best_q5[i], i==4?"":", "); printf("]\n");
    printf("Q6: ["); for(int i=0;i<6;i++) printf("%d%s", best_q6[i], i==5?"":", "); printf("]\n");
    printf("Q7: ["); for(int i=0;i<7;i++) printf("%d%s", best_q7[i], i==6?"":", "); printf("]\n");

    return 0;
}

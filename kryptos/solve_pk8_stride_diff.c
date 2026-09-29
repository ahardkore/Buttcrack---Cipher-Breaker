#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 153

static const char *pk8_raw = 
"COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int kr_to_idx[26];
static int idx_to_kr[26];
static int ct[N];

// Theoretical log-probabilities of letter differences in English under Kryptos alphabet
static float log_p_diff_kr[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        kr_to_idx[KRYPTOS[i] - 'A'] = i;
        idx_to_kr[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct[i] = kr_to_idx[pk8_raw[i] - 'A'];
    }

    // Letter frequencies in English
    double freq[26] = {
        0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
        0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
        0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
        0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
        0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
        0.00074
    };

    double p_diff[26] = {0};
    for (int c1 = 0; c1 < 26; c1++) {
        for (int c2 = 0; c2 < 26; c2++) {
            int idx1 = kr_to_idx[c1];
            int idx2 = kr_to_idx[c2];
            int d = (idx2 - idx1 + 26) % 26;
            p_diff[d] += freq[c1] * freq[c2];
        }
    }
    for (int d = 0; d < 26; d++) {
        log_p_diff_kr[d] = (float)log(p_diff[d]);
    }
}

// Score candidate (Q5, Q6) on stride 28 differences
// Stride 28: K[t+28] - K[t] = q5[(t+28)%5] - q5[t%5] + q6[(t+28)%6] - q6[t%6]
// CT[t+28] - CT[t] = PT[t+28] - PT[t] + (K[t+28] - K[t])
// So PT[t+28] - PT[t] = (CT[t+28] - CT[t]) - (K[t+28] - K[t])
float score_q5_q6(const int *q5, const int *q6) {
    float score = 0.0f;
    for (int t = 0; t < N - 28; t++) {
        int dk = (q5[(t + 28) % 5] - q5[t % 5] + q6[(t + 28) % 6] - q6[t % 6] + 52) % 26;
        int dct = (ct[t + 28] - ct[t] + 26) % 26;
        int dpt = (dct - dk + 26) % 26;
        score += log_p_diff_kr[dpt];
    }
    return score;
}

// Score candidate (Q4, Q7) on stride 30 differences
// Stride 30: K[t+30] - K[t] = q4[(t+30)%4] - q4[t%4] + q7[(t+30)%7] - q7[t%7]
float score_q4_q7(const int *q4, const int *q7) {
    float score = 0.0f;
    for (int t = 0; t < N - 30; t++) {
        int dk = (q4[(t + 30) % 4] - q4[t % 4] + q7[(t + 30) % 7] - q7[t % 7] + 52) % 26;
        int dct = (ct[t + 30] - ct[t] + 26) % 26;
        int dpt = (dct - dk + 26) % 26;
        score += log_p_diff_kr[dpt];
    }
    return score;
}

int main() {
    init_tables();
    printf("Starting Stride-Decoupled Solver on PK8...\n");

    // Phase 1: Solve (Q5, Q6) using Stride 28
    printf("Phase 1: Optimizing (Q5, Q6) over 125 Stride-28 equations...\n");
    float global_best_sc_56 = -1e9f;
    int best_q5[5], best_q6[6];

    #pragma omp parallel
    {
        unsigned int seed = 1234567 + omp_get_thread_num() * 88888;
        int local_q5[5], local_q6[6];
        float local_best_sc = -1e9f;

        for (int restart = 0; restart < 50; restart++) {
            int q5[5], q6[6];
            q5[0] = 0;
            for (int i = 1; i < 5; i++) q5[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 6; i++) q6[i] = rand_r(&seed) % 26;

            float cur_sc = score_q5_q6(q5, q6);
            float T = 2.0f;
            float T_min = 0.01f;
            float alpha = 0.9999f;

            for (int step = 0; step < 15000; step++) {
                int var = rand_r(&seed) % 10;
                int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                int old_val;

                if (var < 4) {
                    old_val = q5[var + 1];
                    q5[var + 1] = (old_val + delta) % 26;
                } else {
                    old_val = q6[var - 4];
                    q6[var - 4] = (old_val + delta) % 26;
                }

                float new_sc = score_q5_q6(q5, q6);
                float diff = new_sc - cur_sc;

                if (diff > 0 || expf(diff / T) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = new_sc;
                    if (cur_sc > local_best_sc) {
                        local_best_sc = cur_sc;
                        memcpy(local_q5, q5, sizeof(q5));
                        memcpy(local_q6, q6, sizeof(q6));
                    }
                } else {
                    if (var < 4) q5[var + 1] = old_val;
                    else q6[var - 4] = old_val;
                }

                T *= alpha;
                if (T < T_min) T = T_min;
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc_56) {
                global_best_sc_56 = local_best_sc;
                memcpy(best_q5, local_q5, sizeof(best_q5));
                memcpy(best_q6, local_q6, sizeof(best_q6));
                printf("[Thread %d] New best (Q5, Q6) log-likelihood: %.2f (avg per diff: %.3f)\n",
                       omp_get_thread_num(), global_best_sc_56, global_best_sc_56 / 125.0f);
                printf("  q5: "); for (int i = 0; i < 5; i++) printf("%d ", best_q5[i]); printf("\n");
                printf("  q6: "); for (int i = 0; i < 6; i++) printf("%d ", best_q6[i]); printf("\n");
            }
        }
    }

    printf("\nPhase 1 Complete. Best (Q5, Q6) score: %.2f\n\n", global_best_sc_56);

    // Phase 2: Solve (Q4, Q7) using Stride 30
    printf("Phase 2: Optimizing (Q4, Q7) over 123 Stride-30 equations...\n");
    float global_best_sc_47 = -1e9f;
    int best_q4[4], best_q7[7];

    #pragma omp parallel
    {
        unsigned int seed = 9876543 + omp_get_thread_num() * 77777;
        int local_q4[4], local_q7[7];
        float local_best_sc = -1e9f;

        for (int restart = 0; restart < 50; restart++) {
            int q4[4], q7[7];
            q4[0] = 0;
            for (int i = 1; i < 4; i++) q4[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;

            float cur_sc = score_q4_q7(q4, q7);
            float T = 2.0f;
            float T_min = 0.01f;
            float alpha = 0.9999f;

            for (int step = 0; step < 15000; step++) {
                int var = rand_r(&seed) % 10;
                int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                int old_val;

                if (var < 3) {
                    old_val = q4[var + 1];
                    q4[var + 1] = (old_val + delta) % 26;
                } else {
                    old_val = q7[var - 3];
                    q7[var - 3] = (old_val + delta) % 26;
                }

                float new_sc = score_q4_q7(q4, q7);
                float diff = new_sc - cur_sc;

                if (diff > 0 || expf(diff / T) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = new_sc;
                    if (cur_sc > local_best_sc) {
                        local_best_sc = cur_sc;
                        memcpy(local_q4, q4, sizeof(q4));
                        memcpy(local_q7, q7, sizeof(q7));
                    }
                } else {
                    if (var < 3) q4[var + 1] = old_val;
                    else q7[var - 3] = old_val;
                }

                T *= alpha;
                if (T < T_min) T = T_min;
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc_47) {
                global_best_sc_47 = local_best_sc;
                memcpy(best_q4, local_q4, sizeof(best_q4));
                memcpy(best_q7, local_q7, sizeof(best_q7));
                printf("[Thread %d] New best (Q4, Q7) log-likelihood: %.2f (avg per diff: %.3f)\n",
                       omp_get_thread_num(), global_best_sc_47, global_best_sc_47 / 123.0f);
                printf("  q4: "); for (int i = 0; i < 4; i++) printf("%d ", best_q4[i]); printf("\n");
                printf("  q7: "); for (int i = 0; i < 7; i++) printf("%d ", best_q7[i]); printf("\n");
            }
        }
    }

    printf("\nPhase 2 Complete. Best (Q4, Q7) score: %.2f\n\n", global_best_sc_47);

    return 0;
}

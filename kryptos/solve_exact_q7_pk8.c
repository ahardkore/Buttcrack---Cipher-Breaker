#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const float eng_freq[26] = {
    0.08167f, 0.01492f, 0.02782f, 0.04253f, 0.12702f, 0.02228f, 0.02015f,
    0.06094f, 0.06966f, 0.00153f, 0.00772f, 0.04025f, 0.02406f, 0.06749f,
    0.07507f, 0.01929f, 0.00095f, 0.05987f, 0.06327f, 0.09056f, 0.02758f,
    0.00978f, 0.02360f, 0.00150f, 0.01974f, 0.00074f
};

static float log_p_diff[26];
static float LL60[7][26];

void init_tables(void) {
    float p_diff[26] = {0.0f};
    for (int a = 0; a < 26; a++) {
        for (int b = 0; b < 26; b++) {
            char ca = KRYPTOS[a];
            char cb = KRYPTOS[b];
            int d = (b - a + 26) % 26;
            p_diff[d] += eng_freq[ca - 'A'] * eng_freq[cb - 'A'];
        }
    }
    for (int d = 0; d < 26; d++) log_p_diff[d] = logf(p_diff[d]);

    // Collect stride-60 observations (93 pairs)
    int ct[N];
    for (int i = 0; i < N; i++) ct[i] = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;

    int obs60[7][32];
    int n_obs[7] = {0};
    for (int t = 0; t < N - 60; t++) {
        int p7 = t % 7;
        obs60[p7][n_obs[p7]++] = (ct[t + 60] - ct[t] + 26) % 26;
    }

    // Precompute LL60[p7][delta]
    for (int p7 = 0; p7 < 7; p7++) {
        for (int delta = 0; delta < 26; delta++) {
            float sum = 0.0f;
            for (int k = 0; k < n_obs[p7]; k++) {
                int c_diff = obs60[p7][k];
                sum += log_p_diff[(c_diff - delta + 26) % 26];
            }
            LL60[p7][delta] = sum;
        }
    }
}

int main(void) {
    init_tables();

    // Valid choices respecting parity: q7_parity = [0, 1, 1, 1, 0, 0, 0]
    // Fix q7[0] = 0 (gauge condition)
    int c_even[13], c_odd[13];
    for (int i = 0; i < 13; i++) {
        c_even[i] = i * 2;
        c_odd[i] = i * 2 + 1;
    }

    printf("======================================================================\n");
    printf("EXHAUSTIVE GLOBAL ML EVALUATION OF ALL 4,826,809 Q7 STATES VIA STRIDE 60\n");
    printf("======================================================================\n");

    float global_best_ll = -1e9f;
    int best_q7[7];

    #pragma omp parallel
    {
        float loc_best_ll = -1e9f;
        int loc_best_q7[7];

        #pragma omp for schedule(dynamic)
        for (int i1 = 0; i1 < 13; i1++) {
            int q1 = c_odd[i1];
            for (int i2 = 0; i2 < 13; i2++) {
                int q2 = c_odd[i2];
                for (int i3 = 0; i3 < 13; i3++) {
                    int q3 = c_odd[i3];
                    for (int i4 = 0; i4 < 13; i4++) {
                        int q4 = c_even[i4];
                        // d0 = q4 - q0 = q4
                        float ll0 = LL60[0][q4];

                        for (int i5 = 0; i5 < 13; i5++) {
                            int q5 = c_even[i5];
                            // d1 = q5 - q1
                            int d1 = (q5 - q1 + 26) % 26;
                            float ll1 = ll0 + LL60[1][d1];

                            for (int i6 = 0; i6 < 13; i6++) {
                                int q6 = c_even[i6];
                                int d2 = (q6 - q2 + 26) % 26;
                                int d3 = (0 - q3 + 26) % 26;
                                int d4 = (q1 - q4 + 26) % 26;
                                int d5 = (q2 - q5 + 26) % 26;
                                int d6 = (q3 - q6 + 26) % 26;

                                float tot_ll = ll1 + LL60[2][d2] + LL60[3][d3] + LL60[4][d4] + LL60[5][d5] + LL60[6][d6];

                                if (tot_ll > loc_best_ll) {
                                    loc_best_ll = tot_ll;
                                    loc_best_q7[0] = 0;
                                    loc_best_q7[1] = q1;
                                    loc_best_q7[2] = q2;
                                    loc_best_q7[3] = q3;
                                    loc_best_q7[4] = q4;
                                    loc_best_q7[5] = q5;
                                    loc_best_q7[6] = q6;
                                }
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best_ll > global_best_ll) {
                global_best_ll = loc_best_ll;
                memcpy(best_q7, loc_best_q7, sizeof(best_q7));
            }
        }
    }

    printf("Search Complete!\n");
    printf("Global Maximum Likelihood Q7 Vector:\n[");
    for (int k = 0; k < 7; k++) printf("%d%s", best_q7[k], k == 6 ? "" : ", ");
    printf("]\n");
    printf("Max Log-Likelihood: %.4f\n", global_best_ll);

    // Print letters in Kryptos alphabet
    printf("Kryptos Letters: ");
    for (int k = 0; k < 7; k++) putchar(KRYPTOS[best_q7[k]]);
    putchar('\n');

    // Print letters in Standard alphabet
    printf("Standard Letters: ");
    for (int k = 0; k < 7; k++) putchar(STANDARD[best_q7[k]]);
    putchar('\n');

    return 0;
}

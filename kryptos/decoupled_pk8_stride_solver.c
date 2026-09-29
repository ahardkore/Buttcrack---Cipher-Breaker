#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 153

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

static double log_diff_prob[26];
static int ct_kr[N];

void init_tables() {
    int hpos[256];
    int k2std[26];
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK8_CT[i]];

    double p_k[26];
    for (int i = 0; i < 26; i++) p_k[i] = eng_freq[k2std[i]];

    double diff_dist[26] = {0};
    for (int a = 0; a < 26; a++) {
        for (int b = 0; b < 26; b++) {
            int d = (a - b + 26) % 26;
            diff_dist[d] += p_k[a] * p_k[b];
        }
    }
    for (int d = 0; d < 26; d++) {
        log_diff_prob[d] = log(diff_dist[d]);
    }
}

int main() {
    init_tables();

    double rand_baseline_84 = 69 * log(1.0 / 26.0);
    double rand_baseline_60 = (93 + 33) * log(1.0 / 26.0);

    // ==========================================
    // STEP 1: SOLVE CLOCK 5 FROM STRIDE 84
    // ==========================================
    printf("========================================\n");
    printf("STEP 1: Exhaustive Sweep of Clock 5 from Stride 84 (69 pairs)\n");
    printf("========================================\n");

    // Precompute difference histograms for Clock 5:
    // Stride 84 mod 5 = 4.
    // For residue r in {0..4}, pair difference has dk = (q5[(r+4)%5] - q5[r] + 26)%26.
    // table_5[r][dk] = sum of log_diff_prob[(c_diff - dk + 26)%26] for all pairs with t%5 == r.
    double table_5[5][26] = {{0}};
    for (int t = 0; t < 69; t++) {
        int r = t % 5;
        int cd = (ct_kr[t + 84] - ct_kr[t] + 26) % 26;
        for (int dk = 0; dk < 26; dk++) {
            table_5[r][dk] += log_diff_prob[(cd - dk + 26) % 26];
        }
    }

    double best_ll_5 = -1e9;
    int best_q5[5] = {0};

    // Fix q5[0] = 0 as gauge
    for (int q1 = 0; q1 < 26; q1++) {
        for (int q2 = 0; q2 < 26; q2++) {
            for (int q3 = 0; q3 < 26; q3++) {
                for (int q4 = 0; q4 < 26; q4++) {
                    int q[5] = {0, q1, q2, q3, q4};
                    double ll = table_5[0][(q[4] - q[0] + 26) % 26]
                              + table_5[1][(q[0] - q[1] + 26) % 26]
                              + table_5[2][(q[1] - q[2] + 26) % 26]
                              + table_5[3][(q[2] - q[3] + 26) % 26]
                              + table_5[4][(q[3] - q[4] + 26) % 26];

                    if (ll > best_ll_5) {
                        best_ll_5 = ll;
                        for (int i = 0; i < 5; i++) best_q5[i] = q[i];
                    }
                }
            }
        }
    }

    printf("Best Log-Likelihood for Clock 5: %.2f (Random baseline: %.2f)\n", best_ll_5, rand_baseline_84);
    printf("Recovered q5: [%d, %d, %d, %d, %d] ('%c%c%c%c%c')\n",
           best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4],
           KRYPTOS[best_q5[0]], KRYPTOS[best_q5[1]], KRYPTOS[best_q5[2]],
           KRYPTOS[best_q5[3]], KRYPTOS[best_q5[4]]);

    // ==========================================
    // STEP 2: SOLVE CLOCK 7 FROM STRIDE 60 & 120 (126 pairs)
    // ==========================================
    printf("\n========================================\n");
    printf("STEP 2: Exhaustive Sweep of Clock 7 from Stride 60 & 120 (126 pairs)\n");
    printf("========================================\n");

    // Stride 60 mod 7 = 4.
    // Stride 120 mod 7 = 1.
    // table_60[r][dk]: dk = (q7[(r+4)%7] - q7[r] + 26)%26.
    // table_120[r][dk]: dk = (q7[(r+1)%7] - q7[r] + 26)%26.
    double table_60[7][26] = {{0}};
    for (int t = 0; t < 93; t++) {
        int r = t % 7;
        int cd = (ct_kr[t + 60] - ct_kr[t] + 26) % 26;
        for (int dk = 0; dk < 26; dk++) {
            table_60[r][dk] += log_diff_prob[(cd - dk + 26) % 26];
        }
    }

    double table_120[7][26] = {{0}};
    for (int t = 0; t < 33; t++) {
        int r = t % 7;
        int cd = (ct_kr[t + 120] - ct_kr[t] + 26) % 26;
        for (int dk = 0; dk < 26; dk++) {
            table_120[r][dk] += log_diff_prob[(cd - dk + 26) % 26];
        }
    }

    double t0 = omp_get_wtime();
    double best_ll_7 = -1e9;
    int best_q7[7] = {0};

    // Parallel sweep over q7[1..6] with q7[0]=0
    #pragma omp parallel
    {
        double loc_best_ll = -1e9;
        int loc_best_q7[7] = {0};

        #pragma omp for schedule(dynamic, 1)
        for (int q1 = 0; q1 < 26; q1++) {
            for (int q2 = 0; q2 < 26; q2++) {
                for (int q3 = 0; q3 < 26; q3++) {
                    for (int q4 = 0; q4 < 26; q4++) {
                        for (int q5 = 0; q5 < 26; q5++) {
                            for (int q6 = 0; q6 < 26; q6++) {
                                int q[7] = {0, q1, q2, q3, q4, q5, q6};

                                // Shift for Stride 60: (q[(r+4)%7] - q[r] + 26)%26
                                // Shift for Stride 120: (q[(r+1)%7] - q[r] + 26)%26
                                double ll = table_60[0][(q[4] - q[0] + 26) % 26]
                                          + table_60[1][(q[5] - q[1] + 26) % 26]
                                          + table_60[2][(q[6] - q[2] + 26) % 26]
                                          + table_60[3][(q[0] - q[3] + 26) % 26]
                                          + table_60[4][(q[1] - q[4] + 26) % 26]
                                          + table_60[5][(q[2] - q[5] + 26) % 26]
                                          + table_60[6][(q[3] - q[6] + 26) % 26]
                                          + table_120[0][(q[1] - q[0] + 26) % 26]
                                          + table_120[1][(q[2] - q[1] + 26) % 26]
                                          + table_120[2][(q[3] - q[2] + 26) % 26]
                                          + table_120[3][(q[4] - q[3] + 26) % 26]
                                          + table_120[4][(q[5] - q[4] + 26) % 26]
                                          + table_120[5][(q[6] - q[5] + 26) % 26]
                                          + table_120[6][(q[0] - q[6] + 26) % 26];

                                if (ll > loc_best_ll) {
                                    loc_best_ll = ll;
                                    for (int i = 0; i < 7; i++) loc_best_q7[i] = q[i];
                                }
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best_ll > best_ll_7) {
                best_ll_7 = loc_best_ll;
                for (int i = 0; i < 7; i++) best_q7[i] = loc_best_q7[i];
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Clock 7 sweep finished in %.3f s\n", elapsed);
    printf("Best Log-Likelihood for Clock 7: %.2f (Random baseline: %.2f)\n", best_ll_7, rand_baseline_60);
    printf("Recovered q7: [%d, %d, %d, %d, %d, %d, %d] ('%c%c%c%c%c%c%c')\n",
           best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6],
           KRYPTOS[best_q7[0]], KRYPTOS[best_q7[1]], KRYPTOS[best_q7[2]],
           KRYPTOS[best_q7[3]], KRYPTOS[best_q7[4]], KRYPTOS[best_q7[5]], KRYPTOS[best_q7[6]]);

    return 0;
}

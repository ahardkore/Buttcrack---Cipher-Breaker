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

static double log_diff_prob_kr[26];
static int ct_kr[N];
static int k2std[26];
static int hpos[256];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK8_CT[i]];

    double p_k[26];
    for (int i = 0; i < 26; i++) p_k[i] = eng_freq[k2std[i]];

    double diff_kr[26] = {0};
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            diff_kr[(a - b + 26) % 26] += p_k[a] * p_k[b];
    for (int d = 0; d < 26; d++) log_diff_prob_kr[d] = log(diff_kr[d]);
}

// Candidates for q7 from PK9
static int top_q7_pk9[5][7] = {
    {0, 1, 22, 18, 4, 23, 12},
    {0, 5, 0, 22, 8, 1, 16},
    {0, 5, 4, 0, 12, 1, 16},
    {0, 1, 0, 22, 8, 23, 12},
    {0, 1, 20, 18, 2, 23, 12}
};

int main() {
    init_tables();

    printf("======================================================================\n");
    printf("Testing PK8 Clocks by Importing PK9 q7 Candidates\n");
    printf("======================================================================\n\n");

    // We check Stride 12 (eliminates 4 and 6, isolates 5)
    // Multiples of 12: d = 12, 24, 36, 48, 60 (mod 5 = 2, 4, 1, 3, 0)
    // Stride 20 (eliminates 4 and 5, isolates 6)
    // Multiples of 20: d = 20, 40, 60 (mod 6 = 2, 4, 0)
    // Stride 30 (eliminates 5 and 6, isolates 4)
    // Multiples of 30: d = 30, 60, 90, 120 (mod 4 = 2, 0, 2, 0)

    double best_overall_ll = -1e9;
    int best_cand_idx = -1;
    int best_rot = -1;
    int best_offset = -1;

    for (int c_idx = 0; c_idx < 5; c_idx++) {
        int base_q7[7];
        memcpy(base_q7, top_q7_pk9[c_idx], 7 * sizeof(int));

        for (int rot = 0; rot < 7; rot++) {
            for (int offset = 0; offset < 26; offset++) {
                int test_q7[7];
                for (int i = 0; i < 7; i++) {
                    test_q7[i] = (base_q7[(i + rot) % 7] + offset) % 26;
                }

                // Compute residual ciphertext after removing q7:
                // rem[t] = (ct_kr[t] - test_q7[t % 7] + 26) % 26
                int rem[N];
                for (int t = 0; t < N; t++) {
                    rem[t] = (ct_kr[t] - test_q7[t % 7] + 26) % 26;
                }

                // Stride 12 evaluation: eliminates Clocks 4 and 6!
                // rem[t + d] - rem[t] = P[t + d] - P[t] + (q5[(t + d)%5] - q5[t%5])
                // Find best q5 for these pairs:
                int s12[] = {12, 24, 36, 48, 72, 84, 96, 108}; // d % 5 != 0
                int n_s12 = sizeof(s12) / sizeof(s12[0]);

                double tab5[5][5][26] = {{{0}}};
                int pairs_count = 0;
                for (int s = 0; s < n_s12; s++) {
                    int d = s12[s];
                    for (int t = 0; t < N - d; t++) {
                        int r1 = t % 5;
                        int r2 = (t + d) % 5;
                        int cd = (rem[t + d] - rem[t] + 26) % 26;
                        for (int dk = 0; dk < 26; dk++) {
                            int d_pt = (cd - dk + 26) % 26;
                            tab5[r1][r2][dk] += log_diff_prob_kr[d_pt];
                        }
                        pairs_count++;
                    }
                }

                // Sweep q5[0..4] with q5[0] = 0 (26^4 = 456,976 states)
                double max_ll5 = -1e9;
                int best_q5[5];
                int q5[5];
                q5[0] = 0;

                for (int k1 = 0; k1 < 26; k1++) {
                    q5[1] = k1;
                    for (int k2 = 0; k2 < 26; k2++) {
                        q5[2] = k2;
                        for (int k3 = 0; k3 < 26; k3++) {
                            q5[3] = k3;
                            for (int k4 = 0; k4 < 26; k4++) {
                                q5[4] = k4;

                                double ll = 0.0;
                                for (int s = 0; s < n_s12; s++) {
                                    int d = s12[s];
                                    for (int r = 0; r < 5; r++) {
                                        int r2 = (r + d) % 5;
                                        int dk = (q5[r2] - q5[r] + 26) % 26;
                                        ll += tab5[r][r2][dk];
                                    }
                                }
                                if (ll > max_ll5) {
                                    max_ll5 = ll;
                                    memcpy(best_q5, q5, 5 * sizeof(int));
                                }
                            }
                        }
                    }
                }

                double rand_baseline = pairs_count * log(1.0 / 26.0);
                double delta = max_ll5 - rand_baseline;

                if (delta > 30.0) {
                    printf(">>> SPIKE DETECTED! Delta = +%.2f <<<\n", delta);
                    printf("  PK9 Candidate %d, Rot %d, Offset %d\n", c_idx + 1, rot, offset);
                    printf("  q7: [%d, %d, %d, %d, %d, %d, %d]\n",
                           test_q7[0], test_q7[1], test_q7[2], test_q7[3], test_q7[4], test_q7[5], test_q7[6]);
                    printf("  q5: [%d, %d, %d, %d, %d]\n\n",
                           best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4]);
                }

                if (max_ll5 > best_overall_ll) {
                    best_overall_ll = max_ll5;
                    best_cand_idx = c_idx;
                    best_rot = rot;
                    best_offset = offset;
                }
            }
        }
    }

    printf("Search complete. Best overall LL delta on Stride 12: %.2f\n",
           best_overall_ll - (780 * log(1.0 / 26.0)));

    return 0;
}

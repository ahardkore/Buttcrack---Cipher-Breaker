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

    // Collect all pairs at strides 30, 60, 90, 120 (where Clocks 5 and 6 are constant)
    int n_pairs = 0;
    int p_t[350], p_dt[350], p_cdiff[350];

    int strides[4] = {30, 60, 90, 120};
    for (int s = 0; s < 4; s++) {
        int d = strides[s];
        for (int t = 0; t < N - d; t++) {
            p_t[n_pairs] = t;
            p_dt[n_pairs] = d;
            p_cdiff[n_pairs] = (ct_kr[t + d] - ct_kr[t] + 26) % 26;
            n_pairs++;
        }
    }

    printf("Total stride-30 multiple pairs (Clocks 5 & 6 eliminated): %d\n", n_pairs);
    double rand_baseline = n_pairs * log(1.0 / 26.0);
    printf("Random Baseline LL: %.2f\n\n", rand_baseline);

    // We can evaluate any candidate (q4, q7) pair against these 312 pairs in microseconds!
    // Let's test the top candidates from Clock 7 against all 26^3 = 17,576 possible q4 keys!

    // Top Clock 7 candidate from stride 60: [0, 19, 7, 4, 12, 6, 6]
    // And Mask 116: [0, 2, 22, 10, 23, 19, 20]
    int test_q7_list[5][7] = {
        {0, 19, 7, 4, 12, 6, 6},   // Rank 1 from Stride 60
        {0, 2, 22, 10, 23, 19, 20}, // Mask 116 from PK9
        {0, 22, 10, 4, 15, 9, 9},   // Rank 3 from Stride 60
        {0, 23, 11, 8, 12, 10, 10}, // Rank 2 from Stride 60
        {0, 2, 9, 10, 10, 6, 7}     // Mask 0 base s13
    };

    const char *q7_names[5] = {
        "Stride 60 Rank 1 ('KNATFSS')",
        "PK9 Mask 116 ('KYVDWNQ')",
        "Stride 60 Rank 3 ('KVDTICC')",
        "Stride 60 Rank 2 ('KWEBFDD')",
        "Mask 0 Base ('KYCDDSA')"
    };

    for (int cand = 0; cand < 5; cand++) {
        int *q7 = test_q7_list[cand];
        printf("--- Testing q7: %s ---\n", q7_names[cand]);

        double best_ll = -1e9;
        int best_q4[4] = {0};

        // Sweep all q4 with q4[0] = 0
        for (int q1 = 0; q1 < 26; q1++) {
            for (int q2 = 0; q2 < 26; q2++) {
                for (int q3 = 0; q3 < 26; q3++) {
                    int q4[4] = {0, q1, q2, q3};
                    double ll = 0.0;

                    for (int i = 0; i < n_pairs; i++) {
                        int t = p_t[i];
                        int d = p_dt[i];
                        int cd = p_cdiff[i];

                        int dk = (q4[(t + d) % 4] - q4[t % 4] + q7[(t + d) % 7] - q7[t % 7] + 52) % 26;
                        int dp = (cd - dk + 26) % 26;
                        ll += log_diff_prob[dp];
                    }

                    if (ll > best_ll) {
                        best_ll = ll;
                        best_q4[0] = 0; best_q4[1] = q1; best_q4[2] = q2; best_q4[3] = q3;
                    }
                }
            }
        }

        printf("  Best LL = %.2f (vs baseline %.2f, delta = +%.2f)\n",
               best_ll, rand_baseline, best_ll - rand_baseline);
        printf("  Best q4 = [%d, %d, %d, %d] ('%c%c%c%c')\n\n",
               best_q4[0], best_q4[1], best_q4[2], best_q4[3],
               KRYPTOS[best_q4[0]], KRYPTOS[best_q4[1]], KRYPTOS[best_q4[2]], KRYPTOS[best_q4[3]]);
    }

    return 0;
}

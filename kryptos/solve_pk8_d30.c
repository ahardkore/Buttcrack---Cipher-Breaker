#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 153
#define N30 (N - 30) // 123

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static int ct_kr[N];
static int d30_ct[N30];

// Expected English letter frequencies (A-Z)
static const double english_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015,
    0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749,
    0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758,
    0.00978, 0.02360, 0.00150, 0.01974, 0.00074
};

static double diff_prob[26];

void init() {
    int std_to_kr[26];
    for (int i = 0; i < 26; i++) std_to_kr[ALPH[i] - 'A'] = i;
    for (int i = 0; i < N; i++) ct_kr[i] = std_to_kr[PK8_CT[i] - 'A'];

    // In Kryptos: C = (P + K) % 26
    // C[t+30] - C[t] = (P[t+30] - P[t]) + (K[t+30] - K[t]) % 26
    for (int t = 0; t < N30; t++) {
        d30_ct[t] = (ct_kr[t+30] - ct_kr[t] + 26) % 26;
    }

    // Difference distribution of English in Kryptos alphabet indexing
    // Let's compute probability of (kr(p1) - kr(p2)) % 26 for p1, p2 drawn from English
    for (int d = 0; d < 26; d++) diff_prob[d] = 0.0;
    for (int c1 = 0; c1 < 26; c1++) {
        for (int c2 = 0; c2 < 26; c2++) {
            int kr1 = std_to_kr[c1];
            int kr2 = std_to_kr[c2];
            int diff = (kr1 - kr2 + 26) % 26;
            diff_prob[diff] += english_freq[c1] * english_freq[c2];
        }
    }
}

int main() {
    init();
    printf("Initialized PK8 difference analysis.\n");
    printf("Difference distribution of English in Kryptos alphabet:\n");
    printf("  diff = 0 (exact match): %.4f (expected matches in 123 diffs: %.2f)\n",
           diff_prob[0], diff_prob[0] * N30);

    // s13 = [0, 2, 9, 10, 10, 6, 7]
    // d7_13 = [9, 8, 1, 9, 10, 7, 8] mod 13
    int d7_13[7] = {9, 8, 1, 9, 10, 7, 8};

    // Generate all 64 valid d7 over Z26 where sum is 0 mod 26
    int d7_cands[64][7];
    int d7_cnt = 0;
    for (int mask = 0; mask < 128; mask++) {
        int test_d7[7];
        int s = 0;
        for (int j = 0; j < 7; j++) {
            test_d7[j] = d7_13[j] + ((mask & (1 << j)) ? 13 : 0);
            s = (s + test_d7[j]) % 26;
        }
        if (s == 0) {
            memcpy(d7_cands[d7_cnt++], test_d7, sizeof(test_d7));
        }
    }
    printf("Generated %d valid parity configurations for d7.\n", d7_cnt);

    // Sweeping all 676 choices of d4 x 64 choices of d7 = 43,264 candidates
    printf("Sweeping all 43,264 candidate (d4, d7) vectors on PK8 Delta_30...\n\n");

    double best_ll = -1e9;
    int best_d4[4] = {0}, best_d7[7] = {0};
    int best_zeroes = 0;
    float best_ioc = 0.0f;

    for (int d4_0 = 0; d4_0 < 26; d4_0++) {
        for (int d4_1 = 0; d4_1 < 26; d4_1++) {
            int d4[4] = {d4_0, d4_1, (26 - d4_0) % 26, (26 - d4_1) % 26};

            for (int k = 0; k < d7_cnt; k++) {
                int *d7 = d7_cands[k];

                // Compute Delta_30 K[t] = d4[t % 4] + d7[t % 7] % 26
                // and compute diff_P[t] = (d30_ct[t] - Delta_30 K[t] + 26) % 26
                int counts[26] = {0};
                double ll = 0.0;
                int zeroes = 0;

                for (int t = 0; t < N30; t++) {
                    int del = (d4[t % 4] + d7[t % 7]) % 26;
                    int diff_p = (d30_ct[t] - del + 26) % 26;
                    counts[diff_p]++;
                    ll += log(diff_prob[diff_p] + 1e-6);
                }
                zeroes = counts[0];

                int num = 0;
                for (int a = 0; a < 26; a++) num += counts[a] * (counts[a] - 1);
                float ioc = (float)num / (float)(N30 * (N30 - 1));

                if (ll > best_ll) {
                    best_ll = ll;
                    memcpy(best_d4, d4, sizeof(d4));
                    memcpy(best_d7, d7, 7 * sizeof(int));
                    best_zeroes = zeroes;
                    best_ioc = ioc;

                    printf(">>> NEW BEST LL: %.2f | Zeroes: %2d | IoC: %.5f | d4: [%d,%d,%d,%d] | d7: [%d,%d,%d,%d,%d,%d,%d] <<<\n",
                           best_ll, best_zeroes, best_ioc,
                           best_d4[0], best_d4[1], best_d4[2], best_d4[3],
                           best_d7[0], best_d7[1], best_d7[2], best_d7[3], best_d7[4], best_d7[5], best_d7[6]);
                }
            }
        }
    }

    printf("\n=== GLOBAL BEST DELTA_30 RESULT ===\n");
    printf("Log-Likelihood: %.2f\n", best_ll);
    printf("Zeroes: %d (Expected: ~8)\n", best_zeroes);
    printf("IoC: %.5f (Random baseline: 0.03846)\n", best_ioc);
    printf("d4: [%d, %d, %d, %d]\n", best_d4[0], best_d4[1], best_d4[2], best_d4[3]);
    printf("d7: [%d, %d, %d, %d, %d, %d, %d]\n", best_d7[0], best_d7[1], best_d7[2], best_d7[3], best_d7[4], best_d7[5], best_d7[6]);

    return 0;
}

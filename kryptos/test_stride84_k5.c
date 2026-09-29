#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

// English monogram frequencies
static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

static double log_diff_prob[26];

void init_diff_probs() {
    int k2std[26];
    for (int i=0; i<26; i++) {
        k2std[i] = ALPH[i] - 'A';
    }

    // Probability of each letter in KRYPTOS indexing
    double p_k[26] = {0};
    for (int i=0; i<26; i++) {
        p_k[i] = eng_freq[k2std[i]];
    }

    // Difference distribution: Delta = (k_a - k_b) mod 26
    double diff_dist[26] = {0};
    for (int a=0; a<26; a++) {
        for (int b=0; b<26; b++) {
            int d = (a - b + 26) % 26;
            diff_dist[d] += p_k[a] * p_k[b];
        }
    }

    printf("English Difference Distribution over KRYPTOS alphabet:\n");
    for (int d=0; d<26; d++) {
        log_diff_prob[d] = log(diff_dist[d]);
    }
}

int main() {
    init_diff_probs();

    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int ct_k[N];
    for (int i=0; i<N; i++) ct_k[i] = k2i[(int)CT[i]];

    // Stride 84
    int S = 84;
    int num_pairs = N - S; // 69 pairs
    printf("Evaluating Stride %d on PK8 (%d pairs)...\n", S, num_pairs);

    // Precompute ct differences: ct_diff[i] = (ct_k[i+84] - ct_k[i] + 26) % 26
    int ct_diff[N];
    for (int i=0; i<num_pairs; i++) {
        ct_diff[i] = (ct_k[i+S] - ct_k[i] + 26) % 26;
    }

    // Sweeping k5: k5[0]=0, k5[1..4] in 0..25 (26^4 = 456,976 states)
    double best_ll = -1e9;
    int best_k5[5] = {0};

    typedef struct {
        double ll;
        int k5[5];
    } Cand;

    #pragma omp parallel
    {
        double local_best_ll = -1e9;
        int local_best_k5[5] = {0};

        #pragma omp for collapse(2) schedule(dynamic, 16)
        for (int k1 = 0; k1 < 26; k1++) {
            for (int k2 = 0; k2 < 26; k2++) {
                int k5[5];
                k5[0] = 0;
                k5[1] = k1;
                k5[2] = k2;
                for (int k3 = 0; k3 < 26; k3++) {
                    k5[3] = k3;
                    for (int k4 = 0; k4 < 26; k4++) {
                        k5[4] = k4;

                        double ll = 0;
                        for (int i = 0; i < num_pairs; i++) {
                            int shift_diff = (k5[(i + S) % 5] - k5[i % 5] + 26) % 26;
                            int pt_diff = (ct_diff[i] - shift_diff + 26) % 26;
                            ll += log_diff_prob[pt_diff];
                        }

                        if (ll > local_best_ll) {
                            local_best_ll = ll;
                            memcpy(local_best_k5, k5, sizeof(k5));
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_ll > best_ll) {
                best_ll = local_best_ll;
                memcpy(best_k5, local_best_k5, sizeof(best_k5));
            }
        }
    }

    printf("Best Log-Likelihood for k5: %.2f\n", best_ll);
    printf("Optimal k5: [%d, %d, %d, %d, %d]\n", best_k5[0], best_k5[1], best_k5[2], best_k5[3], best_k5[4]);

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

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
    for (int i=0; i<26; i++) k2std[i] = ALPH[i] - 'A';
    double p_k[26] = {0};
    for (int i=0; i<26; i++) p_k[i] = eng_freq[k2std[i]];
    double diff_dist[26] = {0};
    for (int a=0; a<26; a++) {
        for (int b=0; b<26; b++) {
            int d = (a - b + 26) % 26;
            diff_dist[d] += p_k[a] * p_k[b];
        }
    }
    for (int d=0; d<26; d++) log_diff_prob[d] = log(diff_dist[d]);
}

typedef struct {
    float ll;
    int k5[5];
} Cand;

int main() {
    init_diff_probs();

    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int ct_k[N];
    for (int i=0; i<N; i++) ct_k[i] = k2i[(int)CT[i]];

    int S = 84;
    int num_pairs = N - S; // 69 pairs
    int ct_diff[N];
    for (int i=0; i<num_pairs; i++) ct_diff[i] = (ct_k[i+S] - ct_k[i] + 26) % 26;

    Cand top_cands[100];
    int n_cands = 0;

    #pragma omp parallel
    {
        Cand local_top[20];
        int local_n = 0;

        #pragma omp for collapse(2) schedule(dynamic, 16)
        for (int k1 = 0; k1 < 26; k1++) {
            for (int k2 = 0; k2 < 26; k2++) {
                int k5[5];
                k5[0] = 0; k5[1] = k1; k5[2] = k2;
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

                        // Maintain top 20 locally
                        if (local_n < 20) {
                            local_top[local_n].ll = (float)ll;
                            memcpy(local_top[local_n].k5, k5, sizeof(k5));
                            local_n++;
                        } else {
                            int min_idx = 0;
                            for (int m=1; m<20; m++) {
                                if (local_top[m].ll < local_top[min_idx].ll) min_idx = m;
                            }
                            if (ll > local_top[min_idx].ll) {
                                local_top[min_idx].ll = (float)ll;
                                memcpy(local_top[min_idx].k5, k5, sizeof(k5));
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            for (int i=0; i<local_n; i++) {
                if (n_cands < 100) {
                    top_cands[n_cands++] = local_top[i];
                } else {
                    int min_idx = 0;
                    for (int m=1; m<100; m++) {
                        if (top_cands[m].ll < top_cands[min_idx].ll) min_idx = m;
                    }
                    if (local_top[i].ll > top_cands[min_idx].ll) {
                        top_cands[min_idx] = local_top[i];
                    }
                }
            }
        }
    }

    // Sort top candidates descending
    for (int i=0; i<n_cands-1; i++) {
        for (int j=i+1; j<n_cands; j++) {
            if (top_cands[j].ll > top_cands[i].ll) {
                Cand tmp = top_cands[i]; top_cands[i] = top_cands[j]; top_cands[j] = tmp;
            }
        }
    }

    printf("Top 15 candidates for k5 from Stride 84:\n");
    for (int i=0; i<15; i++) {
        int *k = top_cands[i].k5;
        printf("[%2d] LL = %6.2f | k5 = [%2d, %2d, %2d, %2d, %2d] | k5[2]-k5[3] = %2d | k5[4] = %2d\n",
               i+1, top_cands[i].ll, k[0], k[1], k[2], k[3], k[4], (k[2]-k[3]+26)%26, k[4]);
    }

    return 0;
}

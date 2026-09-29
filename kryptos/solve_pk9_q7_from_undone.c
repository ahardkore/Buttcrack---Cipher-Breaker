#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *UNDONE = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

static double log_diff_prob_kr[26];
static double log_diff_prob_std[26];
static int ct_kr[N];
static int ct_std[N];
static int k2std[26];
static int hpos[256];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)UNDONE[i]];
        ct_std[i] = UNDONE[i] - 'A';
    }

    // Standard alphabet diffs
    double diff_std[26] = {0};
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            diff_std[(a - b + 26) % 26] += eng_freq[a] * eng_freq[b];
    for (int d = 0; d < 26; d++) log_diff_prob_std[d] = log(diff_std[d]);

    // Kryptos alphabet diffs
    double p_k[26];
    for (int i = 0; i < 26; i++) p_k[i] = eng_freq[k2std[i]];
    double diff_kr[26] = {0};
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            diff_kr[(a - b + 26) % 26] += p_k[a] * p_k[b];
    for (int d = 0; d < 26; d++) log_diff_prob_kr[d] = log(diff_kr[d]);
}

typedef struct {
    int t;
    int d;
    int r1, r2;
    int cd_kr;
    int cd_std;
} Pair;

static Pair pairs[2000];
static int n_pairs = 0;

void collect_pairs() {
    // Strides d = 4, 8, 12, ..., 72 where d % 7 != 0
    int strides[] = {4, 8, 12, 16, 20, 24, 32, 36, 40, 44, 48, 52, 60, 64, 68, 72};
    int n_strides = sizeof(strides) / sizeof(strides[0]);

    for (int s = 0; s < n_strides; s++) {
        int d = strides[s];
        for (int t = 0; t < N - d; t++) {
            Pair *p = &pairs[n_pairs++];
            p->t = t;
            p->d = d;
            p->r1 = t % 7;
            p->r2 = (t + d) % 7;
            p->cd_kr = (ct_kr[t + d] - ct_kr[t] + 26) % 26;
            p->cd_std = (ct_std[t + d] - ct_std[t] + 26) % 26;
        }
    }
    printf("Collected %d multiple-of-4 pairs (Clock 4 eliminated)!\n", n_pairs);
}

// Precomputed pair-difference lookup tables:
// pair_logp[mode][pair_idx][dk7]
static double pair_logp[2][2000][26];

void precompute_logp() {
    for (int p = 0; p < n_pairs; p++) {
        for (int dk7 = 0; dk7 < 26; dk7++) {
            // Mode 0: Kryptos Q3
            int d_pt_kr = (pairs[p].cd_kr - dk7 + 26) % 26;
            pair_logp[0][p][dk7] = log_diff_prob_kr[d_pt_kr];

            // Mode 1: Standard Vigenere
            int d_pt_std = (pairs[p].cd_std - dk7 + 26) % 26;
            pair_logp[1][p][dk7] = log_diff_prob_std[d_pt_std];
        }
    }
}

typedef struct {
    double ll;
    int q7[7];
} Candidate;

int main() {
    init_tables();
    collect_pairs();
    precompute_logp();

    double rand_baseline = n_pairs * log(1.0 / 26.0);
    printf("Random Baseline LL = %.2f\n\n", rand_baseline);

    for (int mode = 0; mode < 2; mode++) {
        printf("====================================================\n");
        printf("Sweeping all 308.9M q7 states under %s...\n", mode == 0 ? "Quagmire III (KRYPTOS)" : "Standard Alphabet");
        printf("====================================================\n");

        double t0 = omp_get_wtime();

        #define TOP_N 10
        Candidate top_cands[TOP_N];
        for (int i = 0; i < TOP_N; i++) top_cands[i].ll = -1e9;

        // Precompute tables per (r1, r2, dk7) to accelerate inner loop:
        // tab[r1][r2][dk7] = sum of pair_logp for all pairs with those residues
        double tab[7][7][26] = {{{0}}};
        for (int p = 0; p < n_pairs; p++) {
            int r1 = pairs[p].r1;
            int r2 = pairs[p].r2;
            for (int dk7 = 0; dk7 < 26; dk7++) {
                tab[r1][r2][dk7] += pair_logp[mode][p][dk7];
            }
        }

        // q7[0] = 0. Loop over q7[1..6] (26^6 = 308,915,776)
        #pragma omp parallel
        {
            Candidate loc_cands[TOP_N];
            for (int i = 0; i < TOP_N; i++) loc_cands[i].ll = -1e9;

            #pragma omp for schedule(dynamic, 1)
            for (int k1 = 0; k1 < 26; k1++) {
                int q[7];
                q[0] = 0;
                q[1] = k1;

                for (int k2 = 0; k2 < 26; k2++) {
                    q[2] = k2;
                    for (int k3 = 0; k3 < 26; k3++) {
                        q[3] = k3;
                        for (int k4 = 0; k4 < 26; k4++) {
                            q[4] = k4;
                            for (int k5 = 0; k5 < 26; k5++) {
                                q[5] = k5;
                                for (int k6 = 0; k6 < 26; k6++) {
                                    q[6] = k6;

                                    double ll = 0.0;
                                    for (int r1 = 0; r1 < 7; r1++) {
                                        for (int r2 = 0; r2 < 7; r2++) {
                                            if (r1 == r2) continue;
                                            int dk = (q[r2] - q[r1] + 26) % 26;
                                            ll += tab[r1][r2][dk];
                                        }
                                    }

                                    if (ll > loc_cands[TOP_N - 1].ll) {
                                        for (int k = 0; k < TOP_N; k++) {
                                            if (ll > loc_cands[k].ll) {
                                                for (int j = TOP_N - 1; j > k; j--) loc_cands[j] = loc_cands[j - 1];
                                                loc_cands[k].ll = ll;
                                                memcpy(loc_cands[k].q7, q, 7 * sizeof(int));
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            #pragma omp critical
            {
                for (int k = 0; k < TOP_N; k++) {
                    double s = loc_cands[k].ll;
                    if (s > top_cands[TOP_N - 1].ll) {
                        for (int j = 0; j < TOP_N; j++) {
                            if (s > top_cands[j].ll) {
                                for (int m = TOP_N - 1; m > j; m--) top_cands[m] = top_cands[m - 1];
                                top_cands[j] = loc_cands[k];
                                break;
                            }
                        }
                    }
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        printf("Search of 308.9M q7 states completed in %.3f s!\n\n", elapsed);

        printf("=== TOP 5 q7 CANDIDATES (Mode %d) ===\n", mode);
        for (int k = 0; k < 5; k++) {
            Candidate *c = &top_cands[k];
            printf("Rank %d: LL = %.2f (delta = +%.2f)\n", k + 1, c->ll, c->ll - rand_baseline);
            printf("  q7: [%d, %d, %d, %d, %d, %d, %d] | KR chars: %c%c%c%c%c%c%c | STD chars: %c%c%c%c%c%c%c\n\n",
                   c->q7[0], c->q7[1], c->q7[2], c->q7[3], c->q7[4], c->q7[5], c->q7[6],
                   KRYPTOS[c->q7[0]], KRYPTOS[c->q7[1]], KRYPTOS[c->q7[2]], KRYPTOS[c->q7[3]],
                   KRYPTOS[c->q7[4]], KRYPTOS[c->q7[5]], KRYPTOS[c->q7[6]],
                   'A' + c->q7[0], 'A' + c->q7[1], 'A' + c->q7[2], 'A' + c->q7[3],
                   'A' + c->q7[4], 'A' + c->q7[5], 'A' + c->q7[6]);
        }
    }

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

// English monogram log probabilities
static double log_english_freq[26];
static const double english_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015,
    0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749,
    0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758,
    0.00978, 0.02360, 0.00150, 0.01974, 0.00074
};

static int ct_kr[N];
static int ct_std[N];
static int kr_to_std[26];
static int std_to_kr[26];

void init() {
    for (int a = 0; a < 26; a++) {
        log_english_freq[a] = log(english_freq[a]);
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
}

// Precompute log likelihood for every slice s (0..27) and every shift v (0..25)
static double slice_ll[4][28][26];

void precompute_slice_ll() {
    for (int mode = 0; mode < 4; mode++) {
        for (int s = 0; s < 28; s++) {
            for (int sh = 0; sh < 26; sh++) {
                double ll = 0.0;
                for (int i = s; i < N; i += 28) {
                    int p_val;
                    if (mode == 0) p_val = (ct_std[i] - sh + 26) % 26;
                    else if (mode == 1) p_val = (sh - ct_std[i] + 26) % 26;
                    else if (mode == 2) {
                        int kr_p = (ct_kr[i] - sh + 26) % 26;
                        p_val = kr_to_std[kr_p];
                    } else { // mode 3: Kryptos Beaufort
                        int kr_p = (sh - ct_kr[i] + 26) % 26;
                        p_val = kr_to_std[kr_p];
                    }
                    ll += log_english_freq[p_val];
                }
                slice_ll[mode][s][sh] = ll;
            }
        }
    }
}

int main() {
    init();
    precompute_slice_ll();
    printf("Precomputed slice log-likelihoods for all 4 modes.\n");
    printf("Exhaustively searching all 26^10 = 1.41e14 (q4, q7) configurations via separable decomposition...\n\n");

    const char *mname[] = {"Vigenere Std", "Beaufort Std", "Vigenere Kryptos", "Beaufort Kryptos"};

    for (int mode = 0; mode < 4; mode++) {
        double best_total_ll = -1e9;
        int best_q4[4] = {0}, best_q7[7] = {0};

        #pragma omp parallel
        {
            double local_best_ll = -1e9;
            int local_best_q4[4] = {0}, local_best_q7[7] = {0};

            #pragma omp for collapse(3) schedule(dynamic)
            for (int q4_1 = 0; q4_1 < 26; q4_1++) {
                for (int q4_2 = 0; q4_2 < 26; q4_2++) {
                    for (int q4_3 = 0; q4_3 < 26; q4_3++) {
                        int cur_q4[4] = {0, q4_1, q4_2, q4_3};
                        int cur_q7[7];
                        double total_ll = 0.0;

                        // For each j in 0..6, independently find best q7[j]
                        for (int j = 0; j < 7; j++) {
                            double best_j_ll = -1e9;
                            int best_v = 0;
                            for (int v = 0; v < 26; v++) {
                                double j_ll = 0.0;
                                // slices s where s % 7 == j
                                // s can be j, j+7, j+14, j+21
                                for (int mult = 0; mult < 4; mult++) {
                                    int s = j + mult * 7;
                                    int sh = (cur_q4[s % 4] + v) % 26;
                                    j_ll += slice_ll[mode][s][sh];
                                }
                                if (j_ll > best_j_ll) {
                                    best_j_ll = j_ll;
                                    best_v = v;
                                }
                            }
                            cur_q7[j] = best_v;
                            total_ll += best_j_ll;
                        }

                        if (total_ll > local_best_ll) {
                            local_best_ll = total_ll;
                            memcpy(local_best_q4, cur_q4, sizeof(cur_q4));
                            memcpy(local_best_q7, cur_q7, sizeof(cur_q7));
                        }
                    }
                }
            }

            #pragma omp critical
            {
                if (local_best_ll > best_total_ll) {
                    best_total_ll = local_best_ll;
                    memcpy(best_q4, local_best_q4, sizeof(best_q4));
                    memcpy(best_q7, local_best_q7, sizeof(best_q7));
                }
            }
        }

        printf("=== Mode %d: %s ===\n", mode, mname[mode]);
        printf("Global Best Log-Likelihood: %.4f (Average LL/char: %.4f)\n", best_total_ll, best_total_ll / N);
        printf("q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
        printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n", best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);

        // Key letters in standard and kryptos
        printf("q4 (Std letters): %c%c%c%c | (Kr letters): %c%c%c%c\n",
               'A'+best_q4[0], 'A'+best_q4[1], 'A'+best_q4[2], 'A'+best_q4[3],
               ALPH[best_q4[0]], ALPH[best_q4[1]], ALPH[best_q4[2]], ALPH[best_q4[3]]);
        printf("q7 (Std letters): %c%c%c%c%c%c%c | (Kr letters): %c%c%c%c%c%c%c\n",
               'A'+best_q7[0], 'A'+best_q7[1], 'A'+best_q7[2], 'A'+best_q7[3], 'A'+best_q7[4], 'A'+best_q7[5], 'A'+best_q7[6],
               ALPH[best_q7[0]], ALPH[best_q7[1]], ALPH[best_q7[2]], ALPH[best_q7[3]], ALPH[best_q7[4]], ALPH[best_q7[5]], ALPH[best_q7[6]]);

        // Print shifts
        printf("28 Shifts: [");
        for (int s = 0; s < 28; s++) {
            int sh = (best_q4[s % 4] + best_q7[s % 7]) % 26;
            printf("%d%s", sh, s==27?"":", ");
        }
        printf("]\n");

        // Chi-Square and Letter Distribution
        int counts[26] = {0};
        for (int i = 0; i < N; i++) {
            int sh = (best_q4[i % 4] + best_q7[i % 7]) % 26;
            int p_val;
            if (mode == 0) p_val = (ct_std[i] - sh + 26) % 26;
            else if (mode == 1) p_val = (sh - ct_std[i] + 26) % 26;
            else if (mode == 2) {
                int kr_p = (ct_kr[i] - sh + 26) % 26;
                p_val = kr_to_std[kr_p];
            } else {
                int kr_p = (sh - ct_kr[i] + 26) % 26;
                p_val = kr_to_std[kr_p];
            }
            counts[p_val]++;
        }
        double chi2 = 0.0;
        for (int a = 0; a < 26; a++) {
            double exp = N * english_freq[a];
            double diff = counts[a] - exp;
            chi2 += (diff * diff) / exp;
        }
        printf("Chi2 vs English: %.2f\n", chi2);
        printf("Letters: ");
        for (int a = 0; a < 26; a++) if (counts[a] > 0) printf("%c:%d ", 'A'+a, counts[a]);
        printf("\n\n");
    }

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

static int ct_kr[N];
static int ct_std[N];
static int k2std[26];
static int coset_counts_kr[7][26];
static int coset_counts_std[7][26];
static double E_std[26];
static double inv_E_std[26];

int main() {
    int hpos[256];
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)PK9_CT[i]];
        ct_std[i] = PK9_CT[i] - 'A';
    }

    for (int c = 0; c < 26; c++) {
        E_std[c] = N * eng_freq[c];
        inv_E_std[c] = 1.0 / E_std[c];
    }

    for (int r = 0; r < 7; r++) {
        for (int c = 0; c < 26; c++) {
            coset_counts_kr[r][c] = 0;
            coset_counts_std[r][c] = 0;
        }
        for (int t = r; t < N; t += 7) {
            coset_counts_kr[r][ct_kr[t]]++;
            coset_counts_std[r][ct_std[t]]++;
        }
    }

    printf("Searching all 308,915,776 period-7 keys for Minimum Chi-Square on PK9...\n");

    for (int mode = 0; mode < 2; mode++) {
        printf("\n--- Mode: %s ---\n", mode == 0 ? "Quagmire III (KRYPTOS)" : "Standard Vigenere (A-Z)");
        double t0 = omp_get_wtime();

        double global_min_chi2 = 1e9;
        int best_k[7] = {0};

        #pragma omp parallel
        {
            double loc_min_chi2 = 1e9;
            int loc_k[7] = {0};

            // Fix k0 = 0
            #pragma omp for schedule(dynamic, 1)
            for (int k1 = 0; k1 < 26; k1++) {
                int counts1[26];
                for (int c = 0; c < 26; c++) {
                    int c0 = mode == 0 ? coset_counts_kr[0][c] : coset_counts_std[0][c];
                    int c1_val = mode == 0 ? coset_counts_kr[1][(c + k1) % 26] : coset_counts_std[1][(c + k1) % 26];
                    counts1[c] = c0 + c1_val;
                }

                for (int k2 = 0; k2 < 26; k2++) {
                    int counts2[26];
                    for (int c = 0; c < 26; c++) {
                        int c2_val = mode == 0 ? coset_counts_kr[2][(c + k2) % 26] : coset_counts_std[2][(c + k2) % 26];
                        counts2[c] = counts1[c] + c2_val;
                    }

                    for (int k3 = 0; k3 < 26; k3++) {
                        int counts3[26];
                        for (int c = 0; c < 26; c++) {
                            int c3_val = mode == 0 ? coset_counts_kr[3][(c + k3) % 26] : coset_counts_std[3][(c + k3) % 26];
                            counts3[c] = counts2[c] + c3_val;
                        }

                        for (int k4 = 0; k4 < 26; k4++) {
                            int counts4[26];
                            for (int c = 0; c < 26; c++) {
                                int c4_val = mode == 0 ? coset_counts_kr[4][(c + k4) % 26] : coset_counts_std[4][(c + k4) % 26];
                                counts4[c] = counts3[c] + c4_val;
                            }

                            for (int k5 = 0; k5 < 26; k5++) {
                                int counts5[26];
                                for (int c = 0; c < 26; c++) {
                                    int c5_val = mode == 0 ? coset_counts_kr[5][(c + k5) % 26] : coset_counts_std[5][(c + k5) % 26];
                                    counts5[c] = counts4[c] + c5_val;
                                }

                                for (int k6 = 0; k6 < 26; k6++) {
                                    int final_counts_std[26] = {0};
                                    for (int c = 0; c < 26; c++) {
                                        int c6_val = mode == 0 ? coset_counts_kr[6][(c + k6) % 26] : coset_counts_std[6][(c + k6) % 26];
                                        int tot = counts5[c] + c6_val;
                                        if (mode == 0) {
                                            final_counts_std[k2std[c]] = tot;
                                        } else {
                                            final_counts_std[c] = tot;
                                        }
                                    }

                                    double chi2 = 0.0;
                                    for (int c = 0; c < 26; c++) {
                                        double diff = final_counts_std[c] - E_std[c];
                                        chi2 += diff * diff * inv_E_std[c];
                                    }

                                    if (chi2 < loc_min_chi2) {
                                        loc_min_chi2 = chi2;
                                        loc_k[0] = 0; loc_k[1] = k1; loc_k[2] = k2;
                                        loc_k[3] = k3; loc_k[4] = k4; loc_k[5] = k5; loc_k[6] = k6;
                                    }
                                }
                            }
                        }
                    }
                }
            }

            #pragma omp critical
            {
                if (loc_min_chi2 < global_min_chi2) {
                    global_min_chi2 = loc_min_chi2;
                    for (int i = 0; i < 7; i++) best_k[i] = loc_k[i];
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        printf("Completed 308M keys in %.3f s\n", elapsed);
        printf("Min Chi2: %.2f (DOF=25, expected English ~25)\n", global_min_chi2);
        printf("Best shift vector k = [%d, %d, %d, %d, %d, %d, %d]\n",
               best_k[0], best_k[1], best_k[2], best_k[3], best_k[4], best_k[5], best_k[6]);

        // Print resulting decrypted text Z
        char Z[N + 1];
        int final_counts[26] = {0};
        for (int t = 0; t < N; t++) {
            int sh = best_k[t % 7];
            if (mode == 0) {
                int p_kr = (ct_kr[t] - sh + 26) % 26;
                Z[t] = 'A' + k2std[p_kr];
            } else {
                Z[t] = 'A' + (ct_std[t] - sh + 26) % 26;
            }
            final_counts[Z[t] - 'A']++;
        }
        Z[N] = '\0';
        printf("Decrypted stream Z:\n%s\n", Z);

        // Compute IoC of Z
        long coinc = 0;
        for (int c = 0; c < 26; c++) coinc += final_counts[c] * (final_counts[c] - 1);
        printf("IoC of Z: %.5f\n", (double)coinc / (N * (N - 1)));
    }

    return 0;
}

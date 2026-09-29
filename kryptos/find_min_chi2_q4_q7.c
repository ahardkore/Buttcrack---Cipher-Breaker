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
static int k2std[26];
static double E_std[26];
static double inv_E_std[26];

static const int s13[7] = {0, 2, 9, 10, 10, 6, 7};

int main() {
    int hpos[256];
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)PK9_CT[i]];
    }

    for (int c = 0; c < 26; c++) {
        E_std[c] = N * eng_freq[c];
        inv_E_std[c] = 1.0 / E_std[c];
    }

    printf("Starting exhaustive sweep of all 58,492,928 (q4, q7_mask) keys for Minimum Chi-Square...\n");
    double t0 = omp_get_wtime();

    double global_min_chi2 = 1e9;
    int best_q4[4] = {0};
    int best_mask = -1;
    int best_q7[7] = {0};

    #pragma omp parallel
    {
        double loc_min_chi2 = 1e9;
        int loc_q4[4] = {0};
        int loc_mask = -1;
        int loc_q7[7] = {0};

        #pragma omp for schedule(dynamic, 1)
        for (int mask = 0; mask < 128; mask++) {
            int q7[7];
            for (int j = 0; j < 7; j++) {
                int b = (mask >> j) & 1;
                q7[j] = (s13[j] + 13 * b) % 26;
            }

            // Compute Y[t] = (ct_kr[t] - q7[t % 7] + 26) % 26
            int Y[N];
            for (int t = 0; t < N; t++) {
                Y[t] = (ct_kr[t] - q7[t % 7] + 26) % 26;
            }

            // Precompute sub-stream histograms for each remainder r in {0..3} and shift s in {0..25}
            int sub_hist[4][26][26] = {{{0}}};
            for (int r = 0; r < 4; r++) {
                for (int t = r; t < N; t += 4) {
                    int y = Y[t];
                    for (int s = 0; s < 26; s++) {
                        int z = (y - s + 26) % 26;
                        sub_hist[r][s][z]++;
                    }
                }
            }

            // Loop over all q4
            for (int q0 = 0; q0 < 26; q0++) {
                int c0[26];
                for (int c = 0; c < 26; c++) c0[c] = sub_hist[0][q0][c];

                for (int q1 = 0; q1 < 26; q1++) {
                    int c1[26];
                    for (int c = 0; c < 26; c++) c1[c] = c0[c] + sub_hist[1][q1][c];

                    for (int q2 = 0; q2 < 26; q2++) {
                        int c2[26];
                        for (int c = 0; c < 26; c++) c2[c] = c1[c] + sub_hist[2][q2][c];

                        for (int q3 = 0; q3 < 26; q3++) {
                            double chi2 = 0.0;
                            for (int c = 0; c < 26; c++) {
                                int tot = c2[c] + sub_hist[3][q3][c];
                                int std_c = k2std[c];
                                double diff = tot - E_std[std_c];
                                chi2 += diff * diff * inv_E_std[std_c];
                            }

                            if (chi2 < loc_min_chi2) {
                                loc_min_chi2 = chi2;
                                loc_mask = mask;
                                loc_q4[0] = q0; loc_q4[1] = q1; loc_q4[2] = q2; loc_q4[3] = q3;
                                for (int j = 0; j < 7; j++) loc_q7[j] = q7[j];
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
                best_mask = loc_mask;
                for (int i = 0; i < 4; i++) best_q4[i] = loc_q4[i];
                for (int i = 0; i < 7; i++) best_q7[i] = loc_q7[i];
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Sweep of 58.5M keys finished in %.3f s\n", elapsed);
    printf("Min Chi2: %.2f (expected English ~25)\n", global_min_chi2);
    printf("Best Mask: %d\n", best_mask);
    printf("q4: [%d, %d, %d, %d] ('%c%c%c%c')\n",
           best_q4[0], best_q4[1], best_q4[2], best_q4[3],
           KRYPTOS[best_q4[0]], KRYPTOS[best_q4[1]], KRYPTOS[best_q4[2]], KRYPTOS[best_q4[3]]);
    printf("q7: [%d, %d, %d, %d, %d, %d, %d] ('%c%c%c%c%c%c%c')\n",
           best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6],
           KRYPTOS[best_q7[0]], KRYPTOS[best_q7[1]], KRYPTOS[best_q7[2]],
           KRYPTOS[best_q7[3]], KRYPTOS[best_q7[4]], KRYPTOS[best_q7[5]], KRYPTOS[best_q7[6]]);

    // Print resulting decrypted text Z
    char Z[N + 1];
    int final_counts[26] = {0};
    for (int t = 0; t < N; t++) {
        int k = (best_q4[t % 4] + best_q7[t % 7]) % 26;
        int p_kr = (ct_kr[t] - k + 26) % 26;
        Z[t] = 'A' + k2std[p_kr];
        final_counts[Z[t] - 'A']++;
    }
    Z[N] = '\0';
    printf("Decrypted stream Z:\n%s\n", Z);

    long coinc = 0;
    for (int c = 0; c < 26; c++) coinc += final_counts[c] * (final_counts[c] - 1);
    printf("IoC of Z: %.5f\n", (double)coinc / (N * (N - 1)));

    return 0;
}

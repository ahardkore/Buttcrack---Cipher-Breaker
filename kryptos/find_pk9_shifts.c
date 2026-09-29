#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

// The TRUE PK9 (144 chars)
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

// Mod-13 base schedule for Clock 7:
// s13 = [0, 2, 9, 10, 10, 6, 7]
static const int s13[7] = {0, 2, 9, 10, 10, 6, 7};

// English monogram frequencies (percentages / 100)
static const float eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015, // A-G
    0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749, // H-N
    0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758, // O-U
    0.00978, 0.02360, 0.00150, 0.01974, 0.00074                    // V-Z
};

int main() {
    int N = strlen(PK9_CT);
    printf("PK9 Length = %d\n", N);

    for (int model = 0; model < 2; model++) {
        const char *alpha = (model == 0) ? KRYPTOS : STD;
        const char *mname = (model == 0) ? "KRYPTOS" : "STD";

        int c_idx[144];
        int alpha_to_std[26];
        for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
        for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK9_CT[i]) - alpha;

        // Precompute counts for each of the 28 slices and 26 possible shifts
        // counts[r][shift][letter]
        int slice_counts[28][26][26] = {0};
        for (int r = 0; r < 28; r++) {
            for (int s = 0; s < 26; s++) {
                for (int i = r; i < N; i += 28) {
                    int p = (c_idx[i] - s + 26) % 26;
                    int std_let = alpha_to_std[p];
                    slice_counts[r][s][std_let]++;
                }
            }
        }

        // Generate 128 Clock 7 candidates from mod-13 base
        int q7_candidates[128][7];
        for (int mask = 0; mask < 128; mask++) {
            for (int j = 0; j < 7; j++) {
                int bit = (mask >> j) & 1;
                q7_candidates[mask][j] = (s13[j] + bit * 13) % 26;
            }
        }

        float best_ioc = 0.0f;
        float best_dot = 0.0f;
        int best_q4[4] = {0}, best_q7[7] = {0};

        #pragma omp parallel
        {
            float local_best_ioc = 0.0f;
            int local_best_q4[4] = {0}, local_best_q7[7] = {0};

            #pragma omp for schedule(dynamic)
            for (int mask = 0; mask < 128; mask++) {
                int q7[7];
                for (int j = 0; j < 7; j++) q7[j] = q7_candidates[mask][j];

                // q4 has gauge q4[0] = 0 (free to fix 0)
                int q4[4];
                q4[0] = 0;

                for (q4[1] = 0; q4[1] < 26; q4[1]++) {
                    for (q4[2] = 0; q4[2] < 26; q4[2]++) {
                        for (q4[3] = 0; q4[3] < 26; q4[3]++) {
                            // Compute total letter counts of Z
                            int tot_counts[26] = {0};
                            for (int r = 0; r < 28; r++) {
                                int shift = (q4[r % 4] + q7[r % 7]) % 26;
                                for (int c = 0; c < 26; c++) {
                                    tot_counts[c] += slice_counts[r][shift][c];
                                }
                            }

                            // Compute monogram IoC of Z
                            int coinc = 0;
                            for (int c = 0; c < 26; c++) {
                                coinc += tot_counts[c] * (tot_counts[c] - 1);
                            }
                            float ioc = (float)coinc / (N * (N - 1));

                            if (ioc > local_best_ioc) {
                                local_best_ioc = ioc;
                                for (int j = 0; j < 4; j++) local_best_q4[j] = q4[j];
                                for (int j = 0; j < 7; j++) local_best_q7[j] = q7[j];
                            }
                        }
                    }
                }
            }

            #pragma omp critical
            {
                if (local_best_ioc > best_ioc) {
                    best_ioc = local_best_ioc;
                    for (int j = 0; j < 4; j++) best_q4[j] = local_best_q4[j];
                    for (int j = 0; j < 7; j++) best_q7[j] = local_best_q7[j];
                }
            }
        }

        printf("[%s] Peak monogram IoC of Z = %6.5f\n", mname, best_ioc);
        printf("  q4 = [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
        printf("  q7 = [%d, %d, %d, %d, %d, %d, %d]\n",
               best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);

        // Print decrypted Z under this peak
        char Z[145];
        for (int i = 0; i < N; i++) {
            int shift = (best_q4[i % 4] + best_q7[i % 7]) % 26;
            int p = (c_idx[i] - shift + 26) % 26;
            Z[i] = 'A' + alpha_to_std[p];
        }
        Z[N] = '\0';
        printf("  Z: %s\n\n", Z);
    }

    return 0;
}

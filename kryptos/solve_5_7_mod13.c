#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
static const char CT[N + 1] = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static const char KRYPTOS[27] = "KRYPTOSABCDEFGHIJLMNQUVWXZ";

// English monogram frequencies mod 13 on KRYPTOS
// Expected mod 13 distribution:
static const float ENG_P13[13] = {
    0.0506, 0.0827, 0.0833, 0.0242, 0.1042, 0.0984, 0.0768,
    0.0913, 0.0381, 0.0901, 0.0841, 0.1384, 0.0378
};

// Compute Chi2 of an observed count vector against ENG_P13
static inline float chi2_mod13(const int *counts, int total) {
    float c2 = 0.0f;
    for (int k = 0; k < 13; k++) {
        float exp_cnt = ENG_P13[k] * total;
        float diff = counts[k] - exp_cnt;
        c2 += (diff * diff) / exp_cnt;
    }
    return c2;
}

int main() {
    int c13[N];
    for (int i = 0; i < N; i++) {
        const char *p = strchr(KRYPTOS, CT[i]);
        int idx = p ? (int)(p - KRYPTOS) : 0;
        c13[i] = idx % 13;
    }

    printf("=== Exhaustive Search of all 13^4 = 28,561 (5, 7) Clocks Mod 13 ===\n");
    double t0 = omp_get_wtime();

    float best_total_chi2 = 1e9f;
    int best_a[5] = {0};
    int best_b[7] = {0};

    // a[0] = 0, a[1..4] in 0..12
    #pragma omp parallel
    {
        float loc_best_chi2 = 1e9f;
        int loc_best_a[5] = {0};
        int loc_best_b[7] = {0};

        #pragma omp for schedule(dynamic, 100)
        for (int idx = 0; idx < 28561; idx++) {
            int a[5];
            a[0] = 0;
            int temp = idx;
            a[1] = temp % 13; temp /= 13;
            a[2] = temp % 13; temp /= 13;
            a[3] = temp % 13; temp /= 13;
            a[4] = temp % 13;

            // Subtract a[i % 5] from c13[i]
            // Slices mod 7
            float cur_chi2_sum = 0.0f;
            int b[7];

            for (int col = 0; col < 7; col++) {
                // Collect counts for slice col
                int counts[13] = {0};
                int col_len = 0;
                for (int i = col; i < N; i += 7) {
                    int val = (c13[i] - a[i % 5]) % 13;
                    if (val < 0) val += 13;
                    counts[val]++;
                    col_len++;
                }

                // Find optimal shift b[col] that minimizes chi2 against ENG_P13
                float min_col_chi2 = 1e9f;
                int opt_shift = 0;

                for (int s = 0; s < 13; s++) {
                    int shifted_counts[13];
                    for (int k = 0; k < 13; k++) {
                        int p = (k - s) % 13;
                        if (p < 0) p += 13;
                        shifted_counts[p] = counts[k];
                    }
                    float c2 = chi2_mod13(shifted_counts, col_len);
                    if (c2 < min_col_chi2) {
                        min_col_chi2 = c2;
                        opt_shift = s;
                    }
                }

                cur_chi2_sum += min_col_chi2;
                b[col] = opt_shift;
            }

            if (cur_chi2_sum < loc_best_chi2) {
                loc_best_chi2 = cur_chi2_sum;
                memcpy(loc_best_a, a, sizeof(int)*5);
                memcpy(loc_best_b, b, sizeof(int)*7);
            }
        }

        #pragma omp critical
        {
            if (loc_best_chi2 < best_total_chi2) {
                best_total_chi2 = loc_best_chi2;
                memcpy(best_a, loc_best_a, sizeof(int)*5);
                memcpy(best_b, loc_best_b, sizeof(int)*7);
            }
        }
    }

    printf("Search completed in %.3f s!\n", omp_get_wtime() - t0);
    printf("Best Total Chi2: %.2f (avg %.2f per col)\n", best_total_chi2, best_total_chi2 / 7.0f);
    printf("Best 5-clock a mod 13: [%d, %d, %d, %d, %d]\n", best_a[0], best_a[1], best_a[2], best_a[3], best_a[4]);
    printf("Best 7-clock b mod 13: [%d, %d, %d, %d, %d, %d, %d]\n", best_b[0], best_b[1], best_b[2], best_b[3], best_b[4], best_b[5], best_b[6]);

    return 0;
}

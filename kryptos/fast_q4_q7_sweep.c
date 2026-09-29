#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const double ENG_FREQ[26] = {
    // English letter frequencies in KRYPTOS alphabet order:
    // K: 0.77, R: 5.99, Y: 1.97, P: 1.93, T: 9.06, O: 7.51, S: 6.33, A: 8.17, B: 1.29, C: 2.78,
    // D: 4.25, E: 12.70, F: 2.23, G: 2.02, H: 6.09, I: 6.97, J: 0.15, L: 4.03, M: 2.41, N: 6.75,
    // Q: 0.10, U: 2.76, V: 0.98, W: 2.36, X: 0.15, Z: 0.07
    0.77, 5.99, 1.97, 1.93, 9.06, 7.51, 6.33, 8.17, 1.29, 2.78,
    4.25, 12.70, 2.23, 2.02, 6.09, 6.97, 0.15, 4.03, 2.41, 6.75,
    0.10, 2.76, 0.98, 2.36, 0.15, 0.07
};

static const int S13[7] = {0, 2, 9, 10, 10, 6, 7};

int main() {
    int ct_idx[N];
    for (int i = 0; i < N; i++) {
        ct_idx[i] = (int)(strchr(ALPH, CT[i]) - ALPH);
    }

    // Generate all 128 candidates for Q7
    int Q7_list[128][7];
    for (int mask = 0; mask < 128; mask++) {
        for (int j = 0; j < 7; j++) {
            int bit = (mask >> j) & 1;
            Q7_list[mask][j] = S13[j] + bit * 13;
        }
    }

    printf("Generated 128 Q7 candidates from halfabet projection.\n");
    printf("Sweeping 128 * 17576 = 2,249,728 (Q4, Q7) pairs with OpenMP...\n");

    double global_best_score = -1e9;
    int best_q4[4] = {0};
    int best_q7[7] = {0};

    #pragma omp parallel for schedule(dynamic)
    for (int mask = 0; mask < 128; mask++) {
        int q7[7];
        memcpy(q7, Q7_list[mask], sizeof(q7));

        for (int a1 = 0; a1 < 26; a1++) {
            for (int a2 = 0; a2 < 26; a2++) {
                for (int a3 = 0; a3 < 26; a3++) {
                    int q4[4] = {0, a1, a2, a3};

                    // Compute frequency dot product of decrypted stream
                    double sc = 0.0;
                    for (int i = 0; i < N; i++) {
                        int k = (q4[i % 4] + q7[i % 7]) % 26;
                        int p = (ct_idx[i] - k + 26) % 26;
                        sc += ENG_FREQ[p];
                    }

                    if (sc > 750.0) {
                        #pragma omp critical
                        {
                            if (sc > global_best_score) {
                                global_best_score = sc;
                                memcpy(best_q4, q4, sizeof(q4));
                                memcpy(best_q7, q7, sizeof(q7));
                                printf("New Best Score: %.2f | Q4=[%d,%d,%d,%d] | Q7=[%d,%d,%d,%d,%d,%d,%d]\n",
                                       sc, q4[0], q4[1], q4[2], q4[3],
                                       q7[0], q7[1], q7[2], q7[3], q7[4], q7[5], q7[6]);
                            }
                        }
                    }
                }
            }
        }
    }

    printf("\n--- GLOBAL OPTIMUM FOUND ---\n");
    printf("Best Score: %.2f (Avg per char: %.2f, English expected: ~6.5)\n",
           global_best_score, global_best_score / N);
    printf("Optimal Q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
    printf("Optimal Q7: [%d, %d, %d, %d, %d, %d, %d]\n",
           best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);

    char pt[N+1];
    for (int i = 0; i < N; i++) {
        int k = (best_q4[i % 4] + best_q7[i % 7]) % 26;
        int p = (ct_idx[i] - k + 26) % 26;
        pt[i] = ALPH[p];
    }
    pt[N] = 0;
    printf("\nDecrypted Transposition Stream T(P):\n%s\n", pt);

    return 0;
}

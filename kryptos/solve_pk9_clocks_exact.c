#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char ALPH[] = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char CT[] = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static const int N = 144;

static const double ENG_FREQ[26] = {
    // KRYPTOSABCDEFGHIJLMNQUVWXZ
    // K: 0.77, R: 5.99, Y: 1.97, P: 1.93, T: 9.06, O: 7.51, S: 6.33, A: 8.17, B: 1.29, C: 2.78,
    // D: 4.25, E: 12.70, F: 2.23, G: 2.02, H: 6.09, I: 6.97, J: 0.15, L: 4.03, M: 2.41, N: 6.75,
    // Q: 0.10, U: 2.76, V: 0.98, W: 2.36, X: 0.15, Z: 0.07
    0.77, 5.99, 1.97, 1.93, 9.06, 7.51, 6.33, 8.17, 1.29, 2.78,
    4.25, 12.70, 2.23, 2.02, 6.09, 6.97, 0.15, 4.03, 2.41, 6.75,
    0.10, 2.76, 0.98, 2.36, 0.15, 0.07
};

static double slice_scores[28][26];

int get_idx(char c) {
    const char *p = strchr(ALPH, c);
    return p ? (int)(p - ALPH) : 0;
}

int main() {
    int ct_idx[144];
    for (int i = 0; i < N; i++) {
        ct_idx[i] = get_idx(CT[i]);
    }

    // Precompute slice_scores[r][shift]
    for (int r = 0; r < 28; r++) {
        for (int shift = 0; shift < 26; shift++) {
            double sum = 0.0;
            for (int i = r; i < N; i += 28) {
                int p_idx = (ct_idx[i] - shift + 26) % 26;
                sum += ENG_FREQ[p_idx];
            }
            slice_scores[r][shift] = sum;
        }
    }

    double global_best_score = -1e9;
    int best_A[4] = {0};
    int best_B[7] = {0};

    // Fix A[0] = 0 without loss of generality (gauge freedom absorbed into B)
    // Actually, let's sweep all 26^4 or fix A[0]=0 and sweep A[1..3] (26^3 = 17,576)
    // Gauge freedom: shifting A by +c and B by -c leaves (A+B) unchanged.
    // So fixing A[0] = 0 covers ALL possible (A+B) streams!
    printf("Sweeping 26^3 = 17,576 choices for A with A[0] = 0...\n");

    for (int a1 = 0; a1 < 26; a1++) {
        for (int a2 = 0; a2 < 26; a2++) {
            for (int a3 = 0; a3 < 26; a3++) {
                int A[4] = {0, a1, a2, a3};
                double total_score = 0.0;
                int curr_B[7];

                for (int j = 0; j < 7; j++) {
                    double best_b_score = -1e9;
                    int best_b_val = 0;
                    for (int b = 0; b < 26; b++) {
                        double s = 0.0;
                        for (int k = 0; k < 4; k++) {
                            int r = j + 7 * k;
                            int shift = (A[r % 4] + b) % 26;
                            s += slice_scores[r][shift];
                        }
                        if (s > best_b_score) {
                            best_b_score = s;
                            best_b_val = b;
                        }
                    }
                    total_score += best_b_score;
                    curr_B[j] = best_b_val;
                }

                if (total_score > global_best_score) {
                    global_best_score = total_score;
                    memcpy(best_A, A, sizeof(A));
                    memcpy(best_B, curr_B, sizeof(curr_B));
                    printf("New best score: %.2f | A: [%d, %d, %d, %d] | B: [%d, %d, %d, %d, %d, %d, %d]\n",
                           global_best_score, A[0], A[1], A[2], A[3],
                           curr_B[0], curr_B[1], curr_B[2], curr_B[3], curr_B[4], curr_B[5], curr_B[6]);
                }
            }
        }
    }

    printf("\n--- GLOBAL OPTIMUM FOUND ---\n");
    printf("Best Score: %.2f (Avg per char: %.2f, Expected random: 3.85, English: ~6.5)\n",
           global_best_score, global_best_score / 144.0);
    printf("Optimal A: [%d, %d, %d, %d]\n", best_A[0], best_A[1], best_A[2], best_A[3]);
    printf("Optimal B: [%d, %d, %d, %d, %d, %d, %d]\n",
           best_B[0], best_B[1], best_B[2], best_B[3], best_B[4], best_B[5], best_B[6]);

    // Decrypt and print the text
    char pt[145];
    for (int i = 0; i < N; i++) {
        int shift = (best_A[i % 4] + best_B[i % 7]) % 26;
        int p_idx = (ct_idx[i] - shift + 26) % 26;
        pt[i] = ALPH[p_idx];
    }
    pt[N] = '\0';
    printf("\nDecrypted Stream (with optimal 2-clock):\n%s\n", pt);

    return 0;
}

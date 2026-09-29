#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const float eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015,
    0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749,
    0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758,
    0.00978, 0.02360, 0.00150, 0.01974, 0.00074
};

static int c_idx[N];
static int alpha_to_std[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
    }
}

// Compute dot contribution for slice j given Q7[j] = v and fixed Q4
float slice_dot(int j, int v, const int *q4) {
    float dot = 0.0f;
    for (int i = j; i < N; i += 7) {
        int k = (q4[i % 4] + v) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        dot += eng_freq[alpha_to_std[p]];
    }
    return dot;
}

int main() {
    init_tables();

    printf("Starting Exact Global Optimization of (Q4, Q7) on PK9...\n");
    printf("Total Q4 space: 26^3 = 17,576 configurations\n");

    float global_best_dot = 0.0f;
    int best_q4[4] = {0};
    int best_q7[7] = {0};

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best_dot = 0.0f;
        int local_best_q4[4] = {0};
        int local_best_q7[7] = {0};

        #pragma omp for schedule(static)
        for (int q4_1 = 0; q4_1 < 26; q4_1++) {
            for (int q4_2 = 0; q4_2 < 26; q4_2++) {
                for (int q4_3 = 0; q4_3 < 26; q4_3++) {
                    int q4[4] = {0, q4_1, q4_2, q4_3};
                    int q7[7];
                    float total_dot = 0.0f;

                    for (int j = 0; j < 7; j++) {
                        float best_j_dot = -1.0f;
                        int best_v = 0;
                        for (int v = 0; v < 26; v++) {
                            float d = slice_dot(j, v, q4);
                            if (d > best_j_dot) {
                                best_j_dot = d;
                                best_v = v;
                            }
                        }
                        q7[j] = best_v;
                        total_dot += best_j_dot;
                    }

                    if (total_dot > local_best_dot) {
                        local_best_dot = total_dot;
                        for (int i = 0; i < 4; i++) local_best_q4[i] = q4[i];
                        for (int j = 0; j < 7; j++) local_best_q7[j] = q7[j];
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_dot > global_best_dot) {
                global_best_dot = local_best_dot;
                for (int i = 0; i < 4; i++) best_q4[i] = local_best_q4[i];
                for (int j = 0; j < 7; j++) best_q7[j] = local_best_q7[j];
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed in %.3f s\n", elapsed);
    printf("Global Best Monogram Dot = %.4f (Expected English: ~9.4, Random: ~6.7)\n", global_best_dot);
    printf("Best Q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
    printf("Best Q7: [%d, %d, %d, %d, %d, %d, %d]\n",
           best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);

    // Decrypt X
    char X[N + 1];
    int counts[26] = {0};
    for (int i = 0; i < N; i++) {
        int k = (best_q4[i % 4] + best_q7[i % 7]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        int std_c = alpha_to_std[p];
        X[i] = 'A' + std_c;
        counts[std_c]++;
    }
    X[N] = '\0';
    printf("\nDecrypted Stream X:\n%s\n", X);

    printf("\nLetter Frequencies in X:\n");
    for (int c = 0; c < 26; c++) {
        printf("%c: %2d (%.1f%%)  ", 'A' + c, counts[c], counts[c] * 100.0 / N);
        if ((c + 1) % 6 == 0) printf("\n");
    }
    printf("\n");

    return 0;
}

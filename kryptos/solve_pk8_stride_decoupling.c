#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 153

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const float eng_freq[26] = {
    0.08167f, 0.01492f, 0.02782f, 0.04253f, 0.12702f, 0.02228f, 0.02015f,
    0.06094f, 0.06966f, 0.00153f, 0.00772f, 0.04025f, 0.02406f, 0.06749f,
    0.07507f, 0.01929f, 0.00095f, 0.05987f, 0.06327f, 0.09056f, 0.02758f,
    0.00978f, 0.02360f, 0.00150f, 0.01974f, 0.00074f
};

static float log_p_diff[26];
static int ct[N];

void init_tables(void) {
    float p_diff[26] = {0.0f};
    for (int a = 0; a < 26; a++) {
        for (int b = 0; b < 26; b++) {
            char ca = KRYPTOS[a];
            char cb = KRYPTOS[b];
            int d = (b - a + 26) % 26;
            p_diff[d] += eng_freq[ca - 'A'] * eng_freq[cb - 'A'];
        }
    }
    for (int d = 0; d < 26; d++) log_p_diff[d] = logf(p_diff[d]);

    for (int i = 0; i < N; i++) ct[i] = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;
}

int main(void) {
    init_tables();

    printf("======================================================================\n");
    printf("ORTHOGONAL STRIDE PROJECTION SOLVER ACROSS ALL 4 CLOCKS OF PK8\n");
    printf("======================================================================\n");

    // 1. Solve Q5 via Stride 84 = lcm(4, 6, 7) -> 84 mod 5 = 4
    // 69 observations: (t + 84) % 5 = (t + 4) % 5
    printf("--- Stage 1: Solving Q5 via Stride 84 (lcm(4,6,7)=84, d mod 5 = 4) ---\n");
    int obs84[5][32];
    int n84[5] = {0};
    for (int t = 0; t < N - 84; t++) {
        int p5 = t % 5;
        obs84[p5][n84[p5]++] = (ct[t + 84] - ct[t] + 26) % 26;
    }

    float LL84[5][26];
    for (int p5 = 0; p5 < 5; p5++) {
        for (int delta = 0; delta < 26; delta++) {
            float sum = 0.0f;
            for (int k = 0; k < n84[p5]; k++) {
                sum += log_p_diff[(obs84[p5][k] - delta + 26) % 26];
            }
            LL84[p5][delta] = sum;
        }
    }

    // Grid search Q5 (fix q5[0] = 0): 26^4 = 456,976 states
    float best_ll5 = -1e9f;
    int best_q5[5];
    for (int q1 = 0; q1 < 26; q1++) {
        for (int q2 = 0; q2 < 26; q2++) {
            for (int q3 = 0; q3 < 26; q3++) {
                for (int q4_val = 0; q4_val < 26; q4_val++) {
                    int d0 = q4_val; // q4 - q0 = q4_val
                    int d1 = (0 - q1 + 26) % 26;
                    int d2 = (q1 - q2 + 26) % 26;
                    int d3 = (q2 - q3 + 26) % 26;
                    int d4 = (q3 - q4_val + 26) % 26;

                    float tot = LL84[0][d0] + LL84[1][d1] + LL84[2][d2] + LL84[3][d3] + LL84[4][d4];
                    if (tot > best_ll5) {
                        best_ll5 = tot;
                        best_q5[0] = 0; best_q5[1] = q1; best_q5[2] = q2; best_q5[3] = q3; best_q5[4] = q4_val;
                    }
                }
            }
        }
    }
    printf("Optimal Q5 Vector:\n[");
    for (int k = 0; k < 5; k++) printf("%d%s", best_q5[k], k == 4 ? "" : ", ");
    printf("] (LL = %.2f)\n", best_ll5);
    printf("Q5 in Kryptos: ");
    for (int k = 0; k < 5; k++) putchar(KRYPTOS[best_q5[k]]);
    putchar('\n');

    // 2. Solve Q6 via Stride 140 = lcm(4, 5, 7) -> 140 mod 6 = 2
    // 13 observations: (t + 140) % 6 = (t + 2) % 6
    printf("\n--- Stage 2: Solving Q6 via Stride 140 (lcm(4,5,7)=140, d mod 6 = 2) ---\n");
    int obs140[6][16];
    int n140[6] = {0};
    for (int t = 0; t < N - 140; t++) {
        int p6 = t % 6;
        obs140[p6][n140[p6]++] = (ct[t + 140] - ct[t] + 26) % 26;
    }

    float LL140[6][26];
    for (int p6 = 0; p6 < 6; p6++) {
        for (int delta = 0; delta < 26; delta++) {
            float sum = 0.0f;
            for (int k = 0; k < n140[p6]; k++) {
                sum += log_p_diff[(obs140[p6][k] - delta + 26) % 26];
            }
            LL140[p6][delta] = sum;
        }
    }

    // Grid search Q6 (fix q6[0] = 0): 26^5 = 11,881,376 states
    float best_ll6 = -1e9f;
    int best_q6[6];
    #pragma omp parallel for collapse(2) schedule(dynamic)
    for (int q1 = 0; q1 < 26; q1++) {
        for (int q2 = 0; q2 < 26; q2++) {
            float loc_ll6 = -1e9f;
            int loc_q6[6];
            for (int q3 = 0; q3 < 26; q3++) {
                for (int q4_val = 0; q4_val < 26; q4_val++) {
                    for (int q5_val = 0; q5_val < 26; q5_val++) {
                        int d0 = q2; // q2 - q0
                        int d1 = (q3 - q1 + 26) % 26;
                        int d2 = (q4_val - q2 + 26) % 26;
                        int d3 = (q5_val - q3 + 26) % 26;
                        int d4 = (0 - q4_val + 26) % 26;
                        int d5 = (q1 - q5_val + 26) % 26;

                        float tot = LL140[0][d0] + LL140[1][d1] + LL140[2][d2] + LL140[3][d3] + LL140[4][d4] + LL140[5][d5];
                        if (tot > loc_ll6) {
                            loc_ll6 = tot;
                            loc_q6[0] = 0; loc_q6[1] = q1; loc_q6[2] = q2; loc_q6[3] = q3; loc_q6[4] = q4_val; loc_q6[5] = q5_val;
                        }
                    }
                }
            }
            #pragma omp critical
            {
                if (loc_ll6 > best_ll6) {
                    best_ll6 = loc_ll6;
                    memcpy(best_q6, loc_q6, sizeof(best_q6));
                }
            }
        }
    }
    printf("Optimal Q6 Vector:\n[");
    for (int k = 0; k < 6; k++) printf("%d%s", best_q6[k], k == 5 ? "" : ", ");
    printf("] (LL = %.2f)\n", best_ll6);
    printf("Q6 in Kryptos: ");
    for (int k = 0; k < 6; k++) putchar(KRYPTOS[best_q6[k]]);
    putchar('\n');

    return 0;
}

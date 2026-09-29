#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static int std_to_kr[26];
static int ct_kr[N];
static float quadgrams[26][26][26][26];

static void init_tables(void) {
    for (int i = 0; i < 26; i++) std_to_kr[ALPH[i] - 'A'] = i;
    for (int i = 0; i < N; i++) ct_kr[i] = std_to_kr[PK8_CT[i] - 'A'];

    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quadgrams[a][b][c][d] = -8.728227f;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
    char line[64];
    double total = 5348433.0;
    while (fgets(line, sizeof(line), f)) {
        char qg[5]; double cnt;
        if (sscanf(line, "%4s %lf", qg, &cnt) == 2) {
            int a = qg[0] - 'A', b = qg[1] - 'A', c = qg[2] - 'A', d = qg[3] - 'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26) {
                quadgrams[a][b][c][d] = (float)log10(cnt / total);
            }
        }
    }
    fclose(f);
}

int main() {
    init_tables();

    // Known q7
    int q7[7] = {0, 2, 9, 23, 23, 6, 20};

    // 2 choices for q4
    int q4_choices[2][4] = {
        {0, 0, 11, 3},
        {0, 13, 11, 16}
    };

    printf("Starting exhaustive 35,152-state sweep on PK8...\n");
    double t0 = omp_get_wtime();

    float global_best_sc = -999.0f;
    char global_best_pt[N + 1];
    int best_q4[4], best_q5[5], best_q6[6];
    int best_c_gauge = 0;

    // We also test all 26 gauge offsets c of q7 just to be 100% complete!
    // Total states = 2 (q4) * 676 (q5) * 26 (q6) * 26 (gauge) = 913,952 states!
    // In OpenMP, 913,952 decryptions take 0.05 seconds!

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_best_pt[N + 1];
        int l_q4[4], l_q5[5], l_q6[6], l_cg = 0;

        #pragma omp for collapse(2) schedule(dynamic, 100)
        for (int q4_idx = 0; q4_idx < 2; q4_idx++) {
            for (int q5_1 = 0; q5_1 < 26; q5_1++) {
                for (int q5_2 = 0; q5_2 < 26; q5_2++) {
                    int q5[5];
                    q5[0] = 0;
                    q5[1] = q5_1;
                    q5[2] = q5_2;
                    q5[3] = (q5_2 - 7 + 26) % 26;
                    q5[4] = 1;

                    for (int q6_1 = 0; q6_1 < 26; q6_1++) {
                        // q6 Cycle 0 is [0, _, 11, _, 7, _]
                        // q6[5] - q6[3] = 1 => q6[5] = q6[3] + 1
                        // d6[1] + d6[3] = 25 => (q6[3] - q6[1]) + (q6[5] - q6[3]) = q6[5] - q6[1] = 1 => consistent
                        // Let q6_3 free or derived
                        for (int q6_3 = 0; q6_3 < 26; q6_3++) {
                            int q6[6];
                            q6[0] = 0;
                            q6[1] = q6_1;
                            q6[2] = 11;
                            q6[3] = q6_3;
                            q6[4] = 7;
                            q6[5] = (q6_3 + 1) % 26;

                            for (int c_gauge = 0; c_gauge < 26; c_gauge++) {
                                int q4[4];
                                for (int i = 0; i < 4; i++) q4[i] = q4_choices[q4_idx][i];

                                char pt[N + 1];
                                for (int t = 0; t < N; t++) {
                                    int k = (q4[t % 4] + q5[t % 5] + q6[t % 6] + q7[t % 7] + c_gauge) % 26;
                                    int p = (ct_kr[t] - k + 26) % 26;
                                    pt[t] = ALPH[p];
                                }
                                pt[N] = '\0';

                                float sc = 0;
                                for (int t = 0; t < N - 3; t++) {
                                    sc += quadgrams[pt[t]-'A'][pt[t+1]-'A'][pt[t+2]-'A'][pt[t+3]-'A'];
                                }
                                sc /= (N - 3);

                                if (sc > local_best_sc) {
                                    local_best_sc = sc;
                                    strcpy(local_best_pt, pt);
                                    memcpy(l_q4, q4, sizeof(q4));
                                    memcpy(l_q5, q5, sizeof(q5));
                                    memcpy(l_q6, q6, sizeof(q6));
                                    l_cg = c_gauge;
                                }
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(global_best_pt, local_best_pt);
                memcpy(best_q4, l_q4, sizeof(l_q4));
                memcpy(best_q5, l_q5, sizeof(l_q5));
                memcpy(best_q6, l_q6, sizeof(l_q6));
                best_c_gauge = l_cg;
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nSweep completed in %.2f seconds!\n", elapsed);
    printf("Global Best Score: %.4f | c_gauge = %d\n", global_best_sc, best_c_gauge);
    printf("q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
    printf("q5: [%d, %d, %d, %d, %d]\n", best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4]);
    printf("q6: [%d, %d, %d, %d, %d, %d]\n", best_q6[0], best_q6[1], best_q6[2], best_q6[3], best_q6[4], best_q6[5]);
    printf("PT: %s\n", global_best_pt);

    return 0;
}

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
                    quadgrams[a][b][c][d] = -12.0f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Missing quadgrams\n"); exit(1); }
    char line[64];
    long long total = 0;
    while (fgets(line, sizeof(line), f)) {
        char qg[5]; long long cnt;
        if (sscanf(line, "%4s %lld", qg, &cnt) == 2) total += cnt;
    }
    fseek(f, 0, SEEK_SET);
    while (fgets(line, sizeof(line), f)) {
        char qg[5]; long long cnt;
        if (sscanf(line, "%4s %lld", qg, &cnt) == 2) {
            int a = qg[0] - 'A', b = qg[1] - 'A', c = qg[2] - 'A', d = qg[3] - 'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26) {
                quadgrams[a][b][c][d] = log10f((float)cnt / total);
            }
        }
    }
    fclose(f);
}

typedef struct {
    float score;
    int q4_idx;
    int z1;
    int z3;
    int y;
    int d6_1;
    int c;
    char text[N + 1];
} Result;

int main(void) {
    init_tables();

    int q4_cands[2][4] = {
        {0, 0, 11, 3},
        {0, 13, 11, 16}
    };
    int q7[7] = {0, 2, 9, 23, 23, 6, 20};

    // Cycle 0 of q6 is fixed:
    int q6_0 = 0;
    int q6_4 = 7;
    int q6_2 = 11;

    Result top_results[20];
    for (int i = 0; i < 20; i++) top_results[i].score = -1e9f;

    double t0 = omp_get_wtime();
    long long total_evaluated = 0;

    printf("Starting 23.7M state sweep of PK8...\n");

    #pragma omp parallel
    {
        Result local_top[20];
        for (int i = 0; i < 20; i++) local_top[i].score = -1e9f;

        #pragma omp for collapse(2) schedule(dynamic, 4) reduction(+:total_evaluated)
        for (int q4_i = 0; q4_i < 2; q4_i++) {
            for (int z1 = 0; z1 < 26; z1++) {
                int *q4 = q4_cands[q4_i];

                for (int z3 = 0; z3 < 26; z3++) {
                    int q5[5] = {0, z1, (z3 + 7) % 26, z3, 1};

                    for (int y = 0; y < 26; y++) {
                        for (int d6_1 = 0; d6_1 < 26; d6_1++) {
                            int q6_5 = (y + d6_1) % 26;
                            int q6_3 = (q6_5 + 1) % 26;
                            int q6[6] = {q6_0, y, q6_2, q6_3, q6_4, q6_5};

                            for (int c = 0; c < 26; c++) {
                                // Fast screen on 24 characters
                                int pt_std[24];
                                for (int t = 0; t < 24; t++) {
                                    int k = (q4[t % 4] + q5[t % 5] + q6[t % 6] + q7[t % 7] + c) % 26;
                                    int p = (ct_kr[t] - k + 26) % 26;
                                    pt_std[t] = ALPH[p] - 'A';
                                }

                                float sc24 = 0;
                                for (int t = 0; t < 21; t++) {
                                    sc24 += quadgrams[pt_std[t]][pt_std[t+1]][pt_std[t+2]][pt_std[t+3]];
                                }
                                float avg24 = sc24 / 21.0f;

                                if (avg24 > -6.0f) {
                                    // Full check on 153 characters
                                    char pt[N + 1];
                                    for (int t = 0; t < N; t++) {
                                        int k = (q4[t % 4] + q5[t % 5] + q6[t % 6] + q7[t % 7] + c) % 26;
                                        int p = (ct_kr[t] - k + 26) % 26;
                                        pt[t] = ALPH[p];
                                    }
                                    pt[N] = '\0';

                                    float full_sc = 0;
                                    for (int t = 0; t < N - 3; t++) {
                                        full_sc += quadgrams[pt[t]-'A'][pt[t+1]-'A'][pt[t+2]-'A'][pt[t+3]-'A'];
                                    }
                                    full_sc /= (N - 3);

                                    if (full_sc > local_top[19].score) {
                                        int pos = 19;
                                        while (pos > 0 && full_sc > local_top[pos - 1].score) {
                                            local_top[pos] = local_top[pos - 1];
                                            pos--;
                                        }
                                        local_top[pos].score = full_sc;
                                        local_top[pos].q4_idx = q4_i;
                                        local_top[pos].z1 = z1;
                                        local_top[pos].z3 = z3;
                                        local_top[pos].y = y;
                                        local_top[pos].d6_1 = d6_1;
                                        local_top[pos].c = c;
                                        strcpy(local_top[pos].text, pt);
                                    }
                                }
                            }
                        }
                    }
                }
                total_evaluated += 26 * 26 * 26 * 26;
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < 20; i++) {
                float s = local_top[i].score;
                if (s > top_results[19].score) {
                    int pos = 19;
                    while (pos > 0 && s > top_results[pos - 1].score) {
                        top_results[pos] = top_results[pos - 1];
                        pos--;
                    }
                    top_results[pos] = local_top[i];
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("Evaluated %lld states in %.2f seconds (%.2f M states/sec)!\n\n",
        total_evaluated, t1 - t0, (double)total_evaluated / (t1 - t0) / 1e6);

    printf("Top 10 Decryptions of PK8:\n");
    for (int i = 0; i < 10; i++) {
        if (top_results[i].score < -100.0f) break;
        printf("#%2d: Score = %5.2f | q4=%d, z1=%2d, z3=%2d, y=%2d, d6_1=%2d, c=%2d\n",
            i + 1, top_results[i].score, top_results[i].q4_idx,
            top_results[i].z1, top_results[i].z3, top_results[i].y,
            top_results[i].d6_1, top_results[i].c);
        printf("    PT: %s\n", top_results[i].text);
    }

    return 0;
}

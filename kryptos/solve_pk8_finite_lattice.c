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
    if (!f) return;
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
    int mode;
    int q4_idx;
    int q5_idx;
    int q6_idx;
    int y;
    int c;
    char text[N + 1];
} Candidate;

int main(void) {
    init_tables();

    // 2 choices for q4
    int q4_cands[2][4] = {
        {0, 0, 11, 3},
        {0, 13, 11, 16}
    };

    // Top 5 choices for q5
    int q5_cands[5][5] = {
        {0, 15, 22, 15, 1},
        {0,  3, 22, 15, 1},
        {0,  0, 21, 14, 1},
        {0, 25, 22, 15, 1},
        {0, 25, 12,  5, 18}
    };

    // Top 5 difference vectors for d6 -> gives cycle0: [0, _, q6_2, _, q6_4, _]
    // and cycle1: [_, y, _, y+d6_3, _, y+d6_1]
    int d6_cands[5][6] = {
        { 7,  0, 15, 25,  4,  1},
        { 7, 20, 15,  5,  4,  1},
        {17,  0,  5, 25,  4,  1},
        { 7,  0, 11, 25,  8,  1},
        { 7,  3, 15, 22,  4,  1}
    };

    int q7[7] = {0, 2, 9, 23, 23, 6, 20};

    Candidate best[20];
    for (int i = 0; i < 20; i++) best[i].score = -1e9f;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        Candidate local_best[20];
        for (int i = 0; i < 20; i++) local_best[i].score = -1e9f;

        #pragma omp for collapse(3) schedule(dynamic, 1)
        for (int q4_i = 0; q4_i < 2; q4_i++) {
            for (int q5_i = 0; q5_i < 5; q5_i++) {
                for (int q6_i = 0; q6_i < 5; q6_i++) {
                    int *q4 = q4_cands[q4_i];
                    int *q5 = q5_cands[q5_i];
                    int *d6 = d6_cands[q6_i];

                    // Cycle 0:
                    // q6[0] = 0
                    // q6[4] = (q6[0] + d6[0]) % 26
                    // q6[2] = (q6[4] + d6[4]) % 26
                    int q6_0 = 0;
                    int q6_4 = (q6_0 + d6[0]) % 26;
                    int q6_2 = (q6_4 + d6[4]) % 26;

                    for (int y = 0; y < 26; y++) {
                        // Cycle 1:
                        // q6[1] = y
                        // q6[5] = (y + d6[1]) % 26
                        // q6[3] = (q6[5] + d6[5]) % 26
                        int q6[6] = {q6_0, y, q6_2, (y + d6[1] + d6[5]) % 26, q6_4, (y + d6[1]) % 26};

                        for (int is_beau = 0; is_beau < 2; is_beau++) {
                            for (int c = 0; c < 26; c++) {
                                char pt[N + 1];
                                for (int t = 0; t < N; t++) {
                                    int k = (q4[t % 4] + q5[t % 5] + q6[t % 6] + q7[t % 7] + c) % 26;
                                    int p = is_beau ? (k - ct_kr[t] + 26) % 26 : (ct_kr[t] - k + 26) % 26;
                                    pt[t] = ALPH[p];
                                }
                                pt[N] = '\0';

                                float sc = 0;
                                for (int t = 0; t < N - 3; t++) {
                                    int a = pt[t] - 'A';
                                    int b = pt[t+1] - 'A';
                                    int cc = pt[t+2] - 'A';
                                    int d = pt[t+3] - 'A';
                                    sc += quadgrams[a][b][cc][d];
                                }
                                float avg_sc = sc / (N - 3);

                                if (avg_sc > local_best[19].score) {
                                    int pos = 19;
                                    while (pos > 0 && avg_sc > local_best[pos - 1].score) {
                                        local_best[pos] = local_best[pos - 1];
                                        pos--;
                                    }
                                    local_best[pos].score = avg_sc;
                                    local_best[pos].mode = is_beau;
                                    local_best[pos].q4_idx = q4_i;
                                    local_best[pos].q5_idx = q5_i;
                                    local_best[pos].q6_idx = q6_i;
                                    local_best[pos].y = y;
                                    local_best[pos].c = c;
                                    strcpy(local_best[pos].text, pt);
                                }
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < 20; i++) {
                float s = local_best[i].score;
                if (s > best[19].score) {
                    int pos = 19;
                    while (pos > 0 && s > best[pos - 1].score) {
                        best[pos] = best[pos - 1];
                        pos--;
                    }
                    best[pos] = local_best[i];
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("Completed sweep in %.3f seconds!\n\n", t1 - t0);

    printf("Top 10 Decryptions of PK8:\n");
    for (int i = 0; i < 10; i++) {
        printf("#%2d: Score = %5.2f | %s | q4=#%d, q5=#%d, q6=#%d, y=%2d, c=%2d\n",
            i + 1, best[i].score, best[i].mode ? "Beaufort" : "Vigenere",
            best[i].q4_idx, best[i].q5_idx, best[i].q6_idx, best[i].y, best[i].c);
        printf("    %s\n", best[i].text);
    }

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static int char_to_kr[256];
static int ct_kr[N];
static float quadgrams[26][26][26][26];

static void init_tables(void) {
    for (int i = 0; i < 26; i++) {
        char_to_kr[(unsigned char)ALPH[i]] = i;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = char_to_kr[(unsigned char)PK8_CT[i]];
    }

    // Initialize quadgrams with floor
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quadgrams[a][b][c][d] = -12.0f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) {
        printf("english_quadgrams.txt not found!\n");
        exit(1);
    }
    char line[64];
    long long total = 0;
    while (fgets(line, sizeof(line), f)) {
        char qg[5];
        long long count;
        if (sscanf(line, "%4s %lld", qg, &count) == 2) {
            total += count;
        }
    }
    fseek(f, 0, SEEK_SET);
    while (fgets(line, sizeof(line), f)) {
        char qg[5];
        long long count;
        if (sscanf(line, "%4s %lld", qg, &count) == 2) {
            int a = qg[0] - 'A';
            int b = qg[1] - 'A';
            int c = qg[2] - 'A';
            int d = qg[3] - 'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26) {
                quadgrams[a][b][c][d] = log10f((float)count / total);
            }
        }
    }
    fclose(f);
}

// Convert Kryptos indices to standard English letters 'A'-'Z'
static inline int kr_to_std_idx(int k) {
    char ch = ALPH[k];
    return ch - 'A';
}

typedef struct {
    float score;
    int x;
    int y;
    int c;
    int q5_idx;
    char text[N + 1];
} Result;

int main(void) {
    init_tables();

    // Top Q5 candidates from stride 84
    int q5_cands[10][5] = {
        { 0,  3, 22, 15,  1 },
        { 0, 15, 22, 15,  1 },
        { 0,  3, 11,  4,  1 },
        { 0, 14, 22, 15,  1 },
        { 0, 15, 21, 14,  1 },
        { 0, 25, 22, 15,  1 },
        { 0,  7,  0, 19,  5 },
        { 0,  3,  0, 19,  5 },
        { 0,  4, 11,  4,  1 },
        { 0, 20,  2, 21,  1 }
    };

    // q7 is fixed
    int q7[7] = {0, 2, 9, 23, 23, 6, 20};

    Result best[20];
    for (int i = 0; i < 20; i++) best[i].score = -1e9f;

    #pragma omp parallel
    {
        Result local_best[20];
        for (int i = 0; i < 20; i++) local_best[i].score = -1e9f;

        #pragma omp for collapse(3) schedule(dynamic, 1)
        for (int q5_i = 0; q5_i < 10; q5_i++) {
            for (int x = 0; x < 26; x++) {
                for (int y = 0; y < 26; y++) {
                    int q4[4] = {0, x, 11, (x + 3) % 26};
                    int q6[6] = {0, y, 14, (y + 1) % 26, 7, y};
                    int *q5 = q5_cands[q5_i];

                    for (int c = 0; c < 26; c++) {
                        // Decrypt PK8 under Vigenere Kryptos
                        // P[t] = (C[t] - K[t]) mod 26
                        char pt[N + 1];
                        int pt_std[N];
                        for (int t = 0; t < N; t++) {
                            int k = (q4[t % 4] + q5[t % 5] + q6[t % 6] + q7[t % 7] + c) % 26;
                            int p_kr = (ct_kr[t] - k + 26) % 26;
                            pt[t] = ALPH[p_kr];
                            pt_std[t] = kr_to_std_idx(p_kr);
                        }
                        pt[N] = '\0';

                        // Score quadgrams
                        float score = 0;
                        for (int t = 0; t < N - 3; t++) {
                            score += quadgrams[pt_std[t]][pt_std[t+1]][pt_std[t+2]][pt_std[t+3]];
                        }

                        if (score > local_best[19].score) {
                            int pos = 19;
                            while (pos > 0 && score > local_best[pos - 1].score) {
                                local_best[pos] = local_best[pos - 1];
                                pos--;
                            }
                            local_best[pos].score = score;
                            local_best[pos].x = x;
                            local_best[pos].y = y;
                            local_best[pos].c = c;
                            local_best[pos].q5_idx = q5_i;
                            strcpy(local_best[pos].text, pt);
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

    printf("Top 10 Decryptions of PK8:\n");
    for (int i = 0; i < 10; i++) {
        printf("#%2d: Score = %7.2f (avg %5.2f) | x=%2d, y=%2d, c=%2d, q5=#%d\n",
            i + 1, best[i].score, best[i].score / (N - 3),
            best[i].x, best[i].y, best[i].c, best[i].q5_idx);
        printf("    %s\n", best[i].text);
    }

    return 0;
}

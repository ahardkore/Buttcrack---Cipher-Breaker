#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int char_to_kr[256];
static int char_to_std[256];
static float quadgrams[26][26][26][26];

static void init_tables(void) {
    for (int i = 0; i < 26; i++) {
        char_to_kr[(unsigned char)ALPH[i]] = i;
        char_to_std['A' + i] = i;
    }
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quadgrams[a][b][c][d] = -12.0f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Cannot open english_quadgrams.txt\n"); exit(1); }
    char line[64];
    long long total = 0;
    while (fgets(line, sizeof(line), f)) {
        char qg[5];
        long long count;
        if (sscanf(line, "%4s %lld", qg, &count) == 2) total += count;
    }
    fseek(f, 0, SEEK_SET);
    while (fgets(line, sizeof(line), f)) {
        char qg[5];
        long long count;
        if (sscanf(line, "%4s %lld", qg, &count) == 2) {
            int a = qg[0] - 'A', b = qg[1] - 'A', c = qg[2] - 'A', d = qg[3] - 'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26) {
                quadgrams[a][b][c][d] = log10f((float)count / total);
            }
        }
    }
    fclose(f);
}

typedef struct {
    float score;
    char w7[8];
    char w8[9];
    char w9[10];
    char pt[64];
} Best;

int main(void) {
    init_tables();

    // Read PK10
    FILE *f = fopen("pk_all_ciphertexts.json", "r");
    if (!f) return 1;
    char buf[4096];
    size_t len = fread(buf, 1, sizeof(buf) - 1, f);
    buf[len] = '\0';
    fclose(f);

    char *p = strstr(buf, "\"PK10\": \"");
    p += 9;
    char *end = strchr(p, '"');
    *end = '\0';

    int C[N];
    for (int i = 0; i < N; i++) C[i] = char_to_kr[(unsigned char)p[i]];

    // Load words
    char w7_list[1000][8];
    int n7 = 0;
    FILE *f7 = fopen("theophilus_w7.txt", "r");
    while (fscanf(f7, "%7s", w7_list[n7]) == 1) {
        if (strlen(w7_list[n7]) == 7) n7++;
    }
    fclose(f7);

    char w8_list[1000][9];
    int n8 = 0;
    FILE *f8 = fopen("theophilus_w8.txt", "r");
    while (fscanf(f8, "%8s", w8_list[n8]) == 1) {
        if (strlen(w8_list[n8]) == 8) n8++;
    }
    fclose(f8);

    char w9_list[1000][10];
    int n9 = 0;
    FILE *f9 = fopen("theophilus_w9.txt", "r");
    while (fscanf(f9, "%9s", w9_list[n9]) == 1) {
        if (strlen(w9_list[n9]) == 9) n9++;
    }
    fclose(f9);

    printf("Loaded Theophilus words: w7=%d, w8=%d, w9=%d -> Total triples: %lld\n",
        n7, n8, n9, (long long)n7 * n8 * n9);

    // Precompute numerical shifts
    int v7[1000][7], v8[1000][8], v9[1000][9];
    for (int i = 0; i < n7; i++)
        for (int j = 0; j < 7; j++) v7[i][j] = char_to_kr[(unsigned char)w7_list[i][j]];
    for (int i = 0; i < n8; i++)
        for (int j = 0; j < 8; j++) v8[i][j] = char_to_kr[(unsigned char)w8_list[i][j]];
    for (int i = 0; i < n9; i++)
        for (int j = 0; j < 9; j++) v9[i][j] = char_to_kr[(unsigned char)w9_list[i][j]];

    Best top[20];
    for (int i = 0; i < 20; i++) top[i].score = -1e9f;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        Best local_top[20];
        for (int i = 0; i < 20; i++) local_top[i].score = -1e9f;

        #pragma omp for collapse(2) schedule(dynamic, 16)
        for (int i7 = 0; i7 < n7; i7++) {
            for (int i8 = 0; i8 < n8; i8++) {
                int *q7 = v7[i7];
                int *q8 = v8[i8];
                for (int i9 = 0; i9 < n9; i9++) {
                    int *q9 = v9[i9];

                    // Fast screening on 32 characters
                    int pt_std[32];
                    for (int t = 0; t < 32; t++) {
                        int k = (q7[t % 7] + q8[t % 8] + q9[t % 9]) % 26;
                        int p_kr = (C[t] - k + 26) % 26;
                        pt_std[t] = ALPH[p_kr] - 'A';
                    }

                    float sc = 0;
                    for (int t = 0; t < 29; t++) {
                        sc += quadgrams[pt_std[t]][pt_std[t+1]][pt_std[t+2]][pt_std[t+3]];
                    }
                    float avg_sc = sc / 29.0f;

                    if (avg_sc > -6.0f) {
                        // Full check on 64 characters
                        int pt64[64];
                        char pt_str[64];
                        for (int t = 0; t < 64; t++) {
                            int k = (q7[t % 7] + q8[t % 8] + q9[t % 9]) % 26;
                            int p_kr = (C[t] - k + 26) % 26;
                            pt_str[t] = ALPH[p_kr];
                            pt64[t] = ALPH[p_kr] - 'A';
                        }
                        pt_str[63] = '\0';

                        float full_sc = 0;
                        for (int t = 0; t < 60; t++) {
                            full_sc += quadgrams[pt64[t]][pt64[t+1]][pt64[t+2]][pt64[t+3]];
                        }
                        full_sc /= 60.0f;

                        if (full_sc > local_top[19].score) {
                            int pos = 19;
                            while (pos > 0 && full_sc > local_top[pos - 1].score) {
                                local_top[pos] = local_top[pos - 1];
                                pos--;
                            }
                            local_top[pos].score = full_sc;
                            strcpy(local_top[pos].w7, w7_list[i7]);
                            strcpy(local_top[pos].w8, w8_list[i8]);
                            strcpy(local_top[pos].w9, w9_list[i9]);
                            strncpy(local_top[pos].pt, pt_str, 63);
                            local_top[pos].pt[63] = '\0';
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < 20; i++) {
                float s = local_top[i].score;
                if (s > top[19].score) {
                    int pos = 19;
                    while (pos > 0 && s > top[pos - 1].score) {
                        top[pos] = top[pos - 1];
                        pos--;
                    }
                    top[pos] = local_top[i];
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("Completed search in %.2f seconds!\n\n", t1 - t0);

    printf("Top Candidates for PK10:\n");
    for (int i = 0; i < 10; i++) {
        if (top[i].score < -100.0f) break;
        printf("#%2d: Score = %5.2f | (%s, %s, %s)\n",
            i + 1, top[i].score, top[i].w7, top[i].w8, top[i].w9);
        printf("    PT: %s\n", top[i].pt);
    }

    return 0;
}

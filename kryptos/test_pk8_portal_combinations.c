#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

static const char ALPH[] = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char CT8[] = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";
static const int N = 153;

static float quad_table[26][26][26][26];

int get_idx(char c) {
    const char *p = strchr(ALPH, c);
    return p ? (int)(p - ALPH) : -1;
}

void load_quads() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -12.0f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Cannot open quadgram file!\n"); exit(1); }
    char line[128]; double total = 0;
    while (fgets(line, sizeof(line), f)) {
        char q[5]; double count;
        if (sscanf(line, "%4s %lf", q, &count) == 2) total += count;
    }
    rewind(f);
    while (fgets(line, sizeof(line), f)) {
        char q[5]; double count;
        if (sscanf(line, "%4s %lf", q, &count) == 2) {
            int i0 = q[0] - 'A', i1 = q[1] - 'A', i2 = q[2] - 'A', i3 = q[3] - 'A';
            if (i0 >= 0 && i0 < 26 && i1 >= 0 && i1 < 26 && i2 >= 0 && i2 < 26 && i3 >= 0 && i3 < 26)
                quad_table[i0][i1][i2][i3] = (float)log10(count / total);
        }
    }
    fclose(f);
}

int main() {
    load_quads();

    // Load wordlists
    FILE *f4 = fopen("curated_w4.txt", "r");
    char w4[1000][8]; int n4 = 0;
    while (fgets(w4[n4], sizeof(w4[n4]), f4)) {
        w4[n4][strcspn(w4[n4], "\r\n")] = 0;
        if (strlen(w4[n4]) == 4) n4++;
    }
    fclose(f4);

    FILE *f5 = fopen("curated_w5.txt", "r");
    char w5[1000][8]; int n5 = 0;
    while (fgets(w5[n5], sizeof(w5[n5]), f5)) {
        w5[n5][strcspn(w5[n5], "\r\n")] = 0;
        if (strlen(w5[n5]) == 5) n5++;
    }
    fclose(f5);

    FILE *f7 = fopen("curated_w7.txt", "r");
    char w7[1000][10]; int n7 = 0;
    while (fgets(w7[n7], sizeof(w7[n7]), f7)) {
        w7[n7][strcspn(w7[n7], "\r\n")] = 0;
        if (strlen(w7[n7]) == 7) n7++;
    }
    fclose(f7);

    printf("Loaded words: w4=%d, w5=%d, w7=%d. Testing with Q6 = 'PORTAL'...\n", n4, n5, n7);

    int ct_idx[153];
    for (int i = 0; i < N; i++) ct_idx[i] = get_idx(CT8[i]);

    int q6[6];
    const char *portal = "PORTAL";
    for (int i = 0; i < 6; i++) q6[i] = get_idx(portal[i]);

    float global_best = -1e9;
    char best_w4[8] = {0}, best_w5[8] = {0}, best_w7[10] = {0};
    char best_pt[154] = {0};

    #pragma omp parallel for schedule(dynamic)
    for (int i4 = 0; i4 < n4; i4++) {
        int k4[4];
        for (int k = 0; k < 4; k++) k4[k] = get_idx(w4[i4][k]);

        for (int i5 = 0; i5 < n5; i5++) {
            int k5[5];
            for (int k = 0; k < 5; k++) k5[k] = get_idx(w5[i5][k]);

            for (int i7 = 0; i7 < n7; i7++) {
                int k7[7];
                for (int k = 0; k < 7; k++) k7[k] = get_idx(w7[i7][k]);

                char pt[154];
                for (int i = 0; i < N; i++) {
                    int shift = (k4[i % 4] + k5[i % 5] + q6[i % 6] + k7[i % 7]) % 26;
                    int p_idx = (ct_idx[i] - shift + 26) % 26;
                    pt[i] = ALPH[p_idx];
                }
                pt[N] = 0;

                float sc = 0;
                for (int i = 0; i < N - 3; i++) {
                    int c0 = pt[i] - 'A', c1 = pt[i+1] - 'A', c2 = pt[i+2] - 'A', c3 = pt[i+3] - 'A';
                    if (c0 >= 0 && c0 < 26 && c1 >= 0 && c1 < 26 && c2 >= 0 && c2 < 26 && c3 >= 0 && c3 < 26)
                        sc += quad_table[c0][c1][c2][c3];
                    else
                        sc += -12.0f;
                }
                sc /= (N - 3);

                if (sc > -7.0f) {
                    #pragma omp critical
                    {
                        if (sc > global_best) {
                            global_best = sc;
                            strcpy(best_w4, w4[i4]);
                            strcpy(best_w5, w5[i5]);
                            strcpy(best_w7, w7[i7]);
                            strcpy(best_pt, pt);
                            printf("HIT! Score: %.4f | w4=%s, w5=%s, w7=%s | PT: %.45s...\n",
                                   sc, best_w4, best_w5, best_w7, best_pt);
                        }
                    }
                }
            }
        }
    }

    printf("Search complete. Global best: %.4f\n", global_best);
    return 0;
}

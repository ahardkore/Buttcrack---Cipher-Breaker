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
static double log_p_diff[26];

static void init_tables(void) {
    for (int i = 0; i < 26; i++) std_to_kr[ALPH[i] - 'A'] = i;
    for (int i = 0; i < N; i++) ct_kr[i] = std_to_kr[PK8_CT[i] - 'A'];

    double eng[26] = {
        0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
        0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
        0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
        0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
        0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
        0.00074
    };
    double diff_prob[26] = {0};
    for (int c1 = 0; c1 < 26; c1++) {
        for (int c2 = 0; c2 < 26; c2++) {
            int kr1 = std_to_kr[c1];
            int kr2 = std_to_kr[c2];
            int diff = (kr1 - kr2 + 26) % 26;
            diff_prob[diff] += eng[c1] * eng[c2];
        }
    }
    for (int d = 0; d < 26; d++) log_p_diff[d] = log(diff_prob[d]);
}

typedef struct {
    double ll;
    int zeroes;
    char w1[16];
    char w2[16];
} Cand;

int main(void) {
    init_tables();

    // ==========================================
    // STAGE 1: Stride 30 -> isolates (w4, w7)
    // 123 pairs
    // ==========================================
    int D30[123];
    for (int t = 0; t < 123; t++) {
        D30[t] = (ct_kr[t + 30] - ct_kr[t] + 26) % 26;
    }

    char w4[1000][8]; int n4 = 0;
    FILE *f4 = fopen("theophilus_w4.txt", "r");
    while (fscanf(f4, "%7s", w4[n4]) == 1) if (strlen(w4[n4]) == 4) n4++;
    fclose(f4);

    char w7[1000][10]; int n7 = 0;
    FILE *f7 = fopen("theophilus_w7.txt", "r");
    while (fscanf(f7, "%9s", w7[n7]) == 1) if (strlen(w7[n7]) == 7) n7++;
    fclose(f7);

    printf("--- Stage 1: Testing (w4, w7) on Stride 30 (%d x %d = %d pairs) ---\n", n4, n7, n4 * n7);

    Cand best30[10];
    for (int i = 0; i < 10; i++) best30[i].ll = -1e9;

    #pragma omp parallel
    {
        Cand local_best[10];
        for (int i = 0; i < 10; i++) local_best[i].ll = -1e9;

        #pragma omp for schedule(dynamic, 100)
        for (int i4 = 0; i4 < n4; i4++) {
            int q4[4];
            for (int j = 0; j < 4; j++) q4[j] = std_to_kr[w4[i4][j] - 'A'];
            int d4[4];
            for (int r = 0; r < 4; r++) d4[r] = (q4[(r + 2) % 4] - q4[r] + 26) % 26;

            for (int i7 = 0; i7 < n7; i7++) {
                int q7[7];
                for (int j = 0; j < 7; j++) q7[j] = std_to_kr[w7[i7][j] - 'A'];
                int d7[7];
                for (int r = 0; r < 7; r++) d7[r] = (q7[(r + 2) % 7] - q7[r] + 26) % 26;

                double ll = 0;
                int zeroes = 0;
                for (int t = 0; t < 123; t++) {
                    int d30_k = (d4[t % 4] + d7[t % 7]) % 26;
                    int diff_P = (D30[t] - d30_k + 26) % 26;
                    ll += log_p_diff[diff_P];
                    if (diff_P == 0) zeroes++;
                }

                if (ll > local_best[9].ll) {
                    int pos = 9;
                    while (pos > 0 && ll > local_best[pos - 1].ll) {
                        local_best[pos] = local_best[pos - 1];
                        pos--;
                    }
                    local_best[pos].ll = ll;
                    local_best[pos].zeroes = zeroes;
                    strcpy(local_best[pos].w1, w4[i4]);
                    strcpy(local_best[pos].w2, w7[i7]);
                }
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < 10; i++) {
                double l = local_best[i].ll;
                if (l > best30[9].ll) {
                    int pos = 9;
                    while (pos > 0 && l > best30[pos - 1].ll) {
                        best30[pos] = best30[pos - 1];
                        pos--;
                    }
                    best30[pos] = local_best[i];
                }
            }
        }
    }

    printf("Top 5 (w4, w7) on Stride 30:\n");
    for (int i = 0; i < 5; i++) {
        printf("#%d: LL=%7.2f | Zeroes=%2d | w4=%s, w7=%s\n",
            i + 1, best30[i].ll, best30[i].zeroes, best30[i].w1, best30[i].w2);
    }

    // ==========================================
    // STAGE 2: Stride 28 -> isolates (w5, w6)
    // 125 pairs
    // ==========================================
    int D28[125];
    for (int t = 0; t < 125; t++) {
        D28[t] = (ct_kr[t + 28] - ct_kr[t] + 26) % 26;
    }

    char w5[1000][8]; int n5 = 0;
    FILE *f5 = fopen("theophilus_w5.txt", "r");
    while (fscanf(f5, "%7s", w5[n5]) == 1) if (strlen(w5[n5]) == 5) n5++;
    fclose(f5);

    char w6[1000][8]; int n6 = 0;
    FILE *f6 = fopen("theophilus_w6.txt", "r");
    while (fscanf(f6, "%7s", w6[n6]) == 1) if (strlen(w6[n6]) == 6) n6++;
    fclose(f6);

    printf("\n--- Stage 2: Testing (w5, w6) on Stride 28 (%d x %d = %d pairs) ---\n", n5, n6, n5 * n6);

    Cand best28[10];
    for (int i = 0; i < 10; i++) best28[i].ll = -1e9;

    #pragma omp parallel
    {
        Cand local_best[10];
        for (int i = 0; i < 10; i++) local_best[i].ll = -1e9;

        #pragma omp for schedule(dynamic, 100)
        for (int i5 = 0; i5 < n5; i5++) {
            int q5[5];
            for (int j = 0; j < 5; j++) q5[j] = std_to_kr[w5[i5][j] - 'A'];
            int d5[5];
            for (int r = 0; r < 5; r++) d5[r] = (q5[(r + 3) % 5] - q5[r] + 26) % 26;

            for (int i6 = 0; i6 < n6; i6++) {
                int q6[6];
                for (int j = 0; j < 6; j++) q6[j] = std_to_kr[w6[i6][j] - 'A'];
                int d6[6];
                for (int r = 0; r < 6; r++) d6[r] = (q6[(r + 4) % 6] - q6[r] + 26) % 26;

                double ll = 0;
                int zeroes = 0;
                for (int t = 0; t < 125; t++) {
                    int d28_k = (d5[t % 5] + d6[t % 6]) % 26;
                    int diff_P = (D28[t] - d28_k + 26) % 26;
                    ll += log_p_diff[diff_P];
                    if (diff_P == 0) zeroes++;
                }

                if (ll > local_best[9].ll) {
                    int pos = 9;
                    while (pos > 0 && ll > local_best[pos - 1].ll) {
                        local_best[pos] = local_best[pos - 1];
                        pos--;
                    }
                    local_best[pos].ll = ll;
                    local_best[pos].zeroes = zeroes;
                    strcpy(local_best[pos].w1, w5[i5]);
                    strcpy(local_best[pos].w2, w6[i6]);
                }
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < 10; i++) {
                double l = local_best[i].ll;
                if (l > best28[9].ll) {
                    int pos = 9;
                    while (pos > 0 && l > best28[pos - 1].ll) {
                        best28[pos] = best28[pos - 1];
                        pos--;
                    }
                    best28[pos] = local_best[i];
                }
            }
        }
    }

    printf("Top 5 (w5, w6) on Stride 28:\n");
    for (int i = 0; i < 5; i++) {
        printf("#%d: LL=%7.2f | Zeroes=%2d | w5=%s, w6=%s\n",
            i + 1, best28[i].ll, best28[i].zeroes, best28[i].w1, best28[i].w2);
    }

    return 0;
}

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
static int ct_std[N];
static float quadgrams[26][26][26][26];

static void init_tables(void) {
    for (int i = 0; i < 26; i++) std_to_kr[ALPH[i] - 'A'] = i;
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK8_CT[i] - 'A'];
        ct_std[i] = PK8_CT[i] - 'A';
    }

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

static inline float score_pt(const int *pt_std) {
    float sc = 0;
    for (int t = 0; t < N - 3; t++) {
        sc += quadgrams[pt_std[t]][pt_std[t+1]][pt_std[t+2]][pt_std[t+3]];
    }
    return sc / (N - 3);
}

int main(void) {
    init_tables();

    float best_sc = -1e9f;
    char best_pt[N + 1];
    char best_primer[16];
    int best_mode = 0;

    printf("1. Sweeping all primers of length L in 1..4 (exhaustive)...\n");

    for (int L = 1; L <= 4; L++) {
        long long total = 1;
        for (int j = 0; j < L; j++) total *= 26;

        #pragma omp parallel
        {
            float local_sc = -1e9f;
            char local_pt[N + 1];
            char local_primer[16];
            int local_mode = 0;

            #pragma omp for schedule(static, 1000)
            for (long long idx = 0; idx < total; idx++) {
                int primer[8];
                long long rem = idx;
                for (int j = L - 1; j >= 0; j--) {
                    primer[j] = rem % 26;
                    rem /= 26;
                }

                // Modes:
                // 0: Kr PT Autokey Vig
                // 1: Kr PT Autokey Beau
                // 2: Kr CT Autokey Vig
                // 3: Kr CT Autokey Beau
                // 4: Std PT Autokey Vig
                // 5: Std PT Autokey Beau
                // 6: Std CT Autokey Vig
                // 7: Std CT Autokey Beau
                for (int m = 0; m < 8; m++) {
                    int use_kr = (m < 4);
                    int is_ct_auto = ((m % 4) >= 2);
                    int is_beau = (m % 2 == 1);
                    const int *ct = use_kr ? ct_kr : ct_std;

                    int pt[N];
                    int pt_std[N];
                    char pt_str[N + 1];

                    for (int t = 0; t < N; t++) {
                        int k;
                        if (t < L) {
                            k = primer[t];
                        } else {
                            k = is_ct_auto ? ct[t - L] : pt[t - L];
                        }

                        int p = is_beau ? (k - ct[t] + 26) % 26 : (ct[t] - k + 26) % 26;
                        pt[t] = p;
                        pt_std[t] = use_kr ? (ALPH[p] - 'A') : p;
                        pt_str[t] = use_kr ? ALPH[p] : ('A' + p);
                    }
                    pt_str[N] = '\0';

                    float sc = score_pt(pt_std);
                    if (sc > local_sc) {
                        local_sc = sc;
                        local_mode = m;
                        strcpy(local_pt, pt_str);
                        for (int j = 0; j < L; j++) local_primer[j] = use_kr ? ALPH[primer[j]] : ('A' + primer[j]);
                        local_primer[L] = '\0';
                    }
                }
            }

            #pragma omp critical
            {
                if (local_sc > best_sc) {
                    best_sc = local_sc;
                    best_mode = local_mode;
                    strcpy(best_pt, local_pt);
                    strcpy(best_primer, local_primer);
                }
            }
        }
        printf("L=%d: Best Score = %5.2f | Primer: %s | Mode: %d\n",
            L, best_sc, best_primer, best_mode);
    }

    printf("\nOverall Best Autokey Result:\n");
    printf("Score = %.2f | Primer: %s | Mode: %d\n", best_sc, best_primer, best_mode);
    printf("PT: %s\n", best_pt);

    return 0;
}

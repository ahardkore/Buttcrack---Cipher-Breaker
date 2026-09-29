#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153
#define STRIDE 70
#define NUM_PAIRS (N - STRIDE) // 83

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static int char_to_kr[256];
static double log_p_diff[26];

static void init_tables(void) {
    for (int i = 0; i < 26; i++) {
        char_to_kr[(unsigned char)ALPH[i]] = i;
    }
    double eng[26] = {
        0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
        0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
        0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
        0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
        0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
        0.00074
    };
    for (int d = 0; d < 26; d++) {
        double sum = 0;
        for (int a = 0; a < 26; a++) {
            sum += eng[a] * eng[(a + d) % 26];
        }
        log_p_diff[d] = log(sum);
    }
}

typedef struct {
    double ll;
    int zeroes;
    int d6[6];
} Cand;

int main(void) {
    init_tables();
    int C[N];
    for (int i = 0; i < N; i++) {
        C[i] = char_to_kr[(unsigned char)PK8_CT[i]];
    }

    // d4 is known: [11, 3, 15, 23]
    int d4[4] = {11, 3, 15, 23};

    int target_D[NUM_PAIRS];
    int t_mod6[NUM_PAIRS];
    for (int t = 0; t < NUM_PAIRS; t++) {
        int d70 = (C[t + STRIDE] - C[t] + 26) % 26;
        // Subtract d4[t % 4]
        target_D[t] = (d70 - d4[t % 4] + 26) % 26;
        t_mod6[t] = t % 6;
    }

    Cand best[20];
    for (int i = 0; i < 20; i++) best[i].ll = -1e9;

    #pragma omp parallel
    {
        Cand local_best[20];
        for (int i = 0; i < 20; i++) local_best[i].ll = -1e9;

        #pragma omp for schedule(static, 1024)
        for (int idx = 0; idx < 456976; idx++) {
            // idx encodes (d6[0], d6[4]) in [0..675] and (d6[1], d6[5]) in [0..675]
            int idx0 = idx / 676;
            int idx1 = idx % 676;

            int d6[6];
            d6[0] = idx0 / 26;
            d6[4] = idx0 % 26;
            d6[2] = (52 - d6[0] - d6[4]) % 26;

            d6[1] = idx1 / 26;
            d6[5] = idx1 % 26;
            d6[3] = (52 - d6[1] - d6[5]) % 26;

            double ll = 0;
            int zeroes = 0;
            for (int t = 0; t < NUM_PAIRS; t++) {
                int r = t_mod6[t];
                int diff_P = (target_D[t] - d6[r] + 26) % 26;
                ll += log_p_diff[diff_P];
                if (diff_P == 0) zeroes++;
            }

            if (ll > local_best[19].ll) {
                int pos = 19;
                while (pos > 0 && ll > local_best[pos - 1].ll) {
                    local_best[pos] = local_best[pos - 1];
                    pos--;
                }
                local_best[pos].ll = ll;
                local_best[pos].zeroes = zeroes;
                memcpy(local_best[pos].d6, d6, sizeof(d6));
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < 20; i++) {
                double ll = local_best[i].ll;
                if (ll > best[19].ll) {
                    int pos = 19;
                    while (pos > 0 && ll > best[pos - 1].ll) {
                        best[pos] = best[pos - 1];
                        pos--;
                    }
                    best[pos] = local_best[i];
                }
            }
        }
    }

    printf("Top 10 candidates for d6 at stride 70:\n");
    for (int i = 0; i < 10; i++) {
        printf("#%2d: LL = %8.2f | Zeroes = %2d | d6 = [%2d, %2d, %2d, %2d, %2d, %2d]\n",
            i + 1, best[i].ll, best[i].zeroes,
            best[i].d6[0], best[i].d6[1], best[i].d6[2], best[i].d6[3], best[i].d6[4], best[i].d6[5]);
    }

    return 0;
}

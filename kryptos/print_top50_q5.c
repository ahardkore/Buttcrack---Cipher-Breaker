#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153
#define STRIDE 84
#define NUM_PAIRS (N - STRIDE)

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static int std_to_kr[26];
static double log_p_diff[26];

static void init_tables(void) {
    for (int i = 0; i < 26; i++) std_to_kr[ALPH[i] - 'A'] = i;
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
    int q5[5];
} Cand;

int main(void) {
    init_tables();
    int C[N];
    for (int i = 0; i < N; i++) C[i] = std_to_kr[PK8_CT[i] - 'A'];

    int D84[NUM_PAIRS];
    int t_mod5[NUM_PAIRS];
    for (int t = 0; t < NUM_PAIRS; t++) {
        D84[t] = (C[t + STRIDE] - C[t] + 26) % 26;
        t_mod5[t] = t % 5;
    }

    Cand best[50];
    for (int i = 0; i < 50; i++) best[i].ll = -1e9;

    #pragma omp parallel
    {
        Cand local_best[50];
        for (int i = 0; i < 50; i++) local_best[i].ll = -1e9;

        #pragma omp for schedule(static, 1024)
        for (int idx = 0; idx < 456976; idx++) {
            int q5[5];
            q5[0] = 0;
            int rem = idx;
            q5[4] = rem % 26; rem /= 26;
            q5[3] = rem % 26; rem /= 26;
            q5[2] = rem % 26; rem /= 26;
            q5[1] = rem % 26;

            int d84_k[5];
            for (int r = 0; r < 5; r++) d84_k[r] = (q5[(r + 4) % 5] - q5[r] + 26) % 26;

            double ll = 0;
            int zeroes = 0;
            for (int t = 0; t < NUM_PAIRS; t++) {
                int r = t_mod5[t];
                int diff_P = (D84[t] - d84_k[r] + 26) % 26;
                ll += log_p_diff[diff_P];
                if (diff_P == 0) zeroes++;
            }

            if (ll > local_best[49].ll) {
                int pos = 49;
                while (pos > 0 && ll > local_best[pos - 1].ll) {
                    local_best[pos] = local_best[pos - 1];
                    pos--;
                }
                local_best[pos].ll = ll;
                local_best[pos].zeroes = zeroes;
                memcpy(local_best[pos].q5, q5, sizeof(q5));
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < 50; i++) {
                double ll = local_best[i].ll;
                if (ll > best[49].ll) {
                    int pos = 49;
                    while (pos > 0 && ll > best[pos - 1].ll) {
                        best[pos] = best[pos - 1];
                        pos--;
                    }
                    best[pos] = local_best[i];
                }
            }
        }
    }

    printf("Ranked by Zeroes first, then LL:\n");
    // Sort best by zeroes descending
    for (int i = 0; i < 50; i++) {
        for (int j = i + 1; j < 50; j++) {
            if (best[j].zeroes > best[i].zeroes || (best[j].zeroes == best[i].zeroes && best[j].ll > best[i].ll)) {
                Cand t = best[i]; best[i] = best[j]; best[j] = t;
            }
        }
    }

    for (int i = 0; i < 20; i++) {
        printf("#%2d: Zeroes = %2d | LL = %7.2f | q5 = [%2d, %2d, %2d, %2d, %2d] | %c%c%c%c%c\n",
            i + 1, best[i].zeroes, best[i].ll,
            best[i].q5[0], best[i].q5[1], best[i].q5[2], best[i].q5[3], best[i].q5[4],
            ALPH[best[i].q5[0]], ALPH[best[i].q5[1]], ALPH[best[i].q5[2]], ALPH[best[i].q5[3]], ALPH[best[i].q5[4]]);
    }

    return 0;
}

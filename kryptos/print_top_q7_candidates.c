#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 153

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

static double log_diff_prob[26];
static int ct_kr[N];

void init_tables() {
    int hpos[256];
    int k2std[26];
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK8_CT[i]];

    double p_k[26];
    for (int i = 0; i < 26; i++) p_k[i] = eng_freq[k2std[i]];

    double diff_dist[26] = {0};
    for (int a = 0; a < 26; a++) {
        for (int b = 0; b < 26; b++) {
            int d = (a - b + 26) % 26;
            diff_dist[d] += p_k[a] * p_k[b];
        }
    }
    for (int d = 0; d < 26; d++) {
        log_diff_prob[d] = log(diff_dist[d]);
    }
}

typedef struct {
    double ll;
    int q[7];
} Cand7;

int main() {
    init_tables();

    double table_60[7][26] = {{0}};
    for (int t = 0; t < 93; t++) {
        int r = t % 7;
        int cd = (ct_kr[t + 60] - ct_kr[t] + 26) % 26;
        for (int dk = 0; dk < 26; dk++) {
            table_60[r][dk] += log_diff_prob[(cd - dk + 26) % 26];
        }
    }

    double table_120[7][26] = {{0}};
    for (int t = 0; t < 33; t++) {
        int r = t % 7;
        int cd = (ct_kr[t + 120] - ct_kr[t] + 26) % 26;
        for (int dk = 0; dk < 26; dk++) {
            table_120[r][dk] += log_diff_prob[(cd - dk + 26) % 26];
        }
    }

    printf("Collecting top candidates for Clock 7 across all 308M states...\n");
    #define TOP_N 30
    Cand7 global_top[TOP_N];
    for (int i = 0; i < TOP_N; i++) global_top[i].ll = -1e9;

    #pragma omp parallel
    {
        Cand7 loc_top[TOP_N];
        for (int i = 0; i < TOP_N; i++) loc_top[i].ll = -1e9;

        #pragma omp for schedule(dynamic, 1)
        for (int q1 = 0; q1 < 26; q1++) {
            for (int q2 = 0; q2 < 26; q2++) {
                for (int q3 = 0; q3 < 26; q3++) {
                    for (int q4 = 0; q4 < 26; q4++) {
                        for (int q5 = 0; q5 < 26; q5++) {
                            for (int q6 = 0; q6 < 26; q6++) {
                                int q[7] = {0, q1, q2, q3, q4, q5, q6};

                                double ll = table_60[0][(q[4] - q[0] + 26) % 26]
                                          + table_60[1][(q[5] - q[1] + 26) % 26]
                                          + table_60[2][(q[6] - q[2] + 26) % 26]
                                          + table_60[3][(q[0] - q[3] + 26) % 26]
                                          + table_60[4][(q[1] - q[4] + 26) % 26]
                                          + table_60[5][(q[2] - q[5] + 26) % 26]
                                          + table_60[6][(q[3] - q[6] + 26) % 26]
                                          + table_120[0][(q[1] - q[0] + 26) % 26]
                                          + table_120[1][(q[2] - q[1] + 26) % 26]
                                          + table_120[2][(q[3] - q[2] + 26) % 26]
                                          + table_120[3][(q[4] - q[3] + 26) % 26]
                                          + table_120[4][(q[5] - q[4] + 26) % 26]
                                          + table_120[5][(q[6] - q[5] + 26) % 26]
                                          + table_120[6][(q[0] - q[6] + 26) % 26];

                                if (ll > loc_top[TOP_N - 1].ll) {
                                    for (int i = 0; i < TOP_N; i++) {
                                        if (ll > loc_top[i].ll) {
                                            for (int j = TOP_N - 1; j > i; j--) loc_top[j] = loc_top[j - 1];
                                            loc_top[i].ll = ll;
                                            for (int k = 0; k < 7; k++) loc_top[i].q[k] = q[k];
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < TOP_N; i++) {
                double ll = loc_top[i].ll;
                if (ll > global_top[TOP_N - 1].ll) {
                    for (int j = 0; j < TOP_N; j++) {
                        if (ll > global_top[j].ll) {
                            for (int k = TOP_N - 1; k > j; k--) global_top[k] = global_top[k - 1];
                            global_top[j].ll = ll;
                            for (int k = 0; k < 7; k++) global_top[j].q[k] = loc_top[i].q[k];
                            break;
                        }
                    }
                }
            }
        }
    }

    printf("=== TOP 20 CANDIDATES FOR CLOCK 7 (STRIDE 60 & 120) ===\n");
    for (int i = 0; i < 20; i++) {
        printf("Rank %2d: LL = %.2f | q7 = [%d, %d, %d, %d, %d, %d, %d] | Letters: %c%c%c%c%c%c%c\n",
               i + 1, global_top[i].ll,
               global_top[i].q[0], global_top[i].q[1], global_top[i].q[2],
               global_top[i].q[3], global_top[i].q[4], global_top[i].q[5], global_top[i].q[6],
               KRYPTOS[global_top[i].q[0]], KRYPTOS[global_top[i].q[1]], KRYPTOS[global_top[i].q[2]],
               KRYPTOS[global_top[i].q[3]], KRYPTOS[global_top[i].q[4]], KRYPTOS[global_top[i].q[5]],
               KRYPTOS[global_top[i].q[6]]);
    }

    return 0;
}

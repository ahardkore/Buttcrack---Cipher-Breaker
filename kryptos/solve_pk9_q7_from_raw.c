#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int ct_std[N];
static int hpos[256];
static int k2std[26];

static float log_diff_prob[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)PK9_RAW[i]];
        ct_std[i] = PK9_RAW[i] - 'A';
    }

    float f[26] = {
        0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015,
        0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749,
        0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758,
        0.00978, 0.02360, 0.00150, 0.01974, 0.00074
    };
    for (int d = 0; d < 26; d++) {
        float p = 0.0f;
        for (int a = 0; a < 26; a++) {
            int b = (a + d) % 26;
            p += f[a] * f[b];
        }
        log_diff_prob[d] = logf(p);
    }
}

static float cost_kr[7][7][26];
static float cost_std[7][7][26];

int main() {
    init_tables();
    memset(cost_kr, 0, sizeof(cost_kr));
    memset(cost_std, 0, sizeof(cost_std));

    int hist_kr[7][7][26] = {0};
    int hist_std[7][7][26] = {0};

    int n_pairs = 0;
    for (int i = 0; i < N; i++) {
        for (int j = i + 1; j < N; j++) {
            int d = j - i;
            if (d % 4 == 0 && d % 7 != 0) {
                int c1 = i % 7;
                int c2 = j % 7;
                int diff_kr = (ct_kr[j] - ct_kr[i] + 26) % 26;
                int diff_std = (ct_std[j] - ct_std[i] + 26) % 26;
                hist_kr[c1][c2][diff_kr]++;
                hist_std[c1][c2][diff_std]++;
                n_pairs++;
            }
        }
    }

    // Precompute cost[c1][c2][k_diff]
    for (int c1 = 0; c1 < 7; c1++) {
        for (int c2 = 0; c2 < 7; c2++) {
            if (c1 >= c2) continue;
            for (int k_diff = 0; k_diff < 26; k_diff++) {
                float s_kr = 0.0f, s_std = 0.0f;
                for (int d = 0; d < 26; d++) {
                    int cnt_kr = hist_kr[c1][c2][d];
                    if (cnt_kr > 0) {
                        int p_diff = (d - k_diff + 26) % 26;
                        s_kr += cnt_kr * log_diff_prob[p_diff];
                    }
                    int cnt_std = hist_std[c1][c2][d];
                    if (cnt_std > 0) {
                        int p_diff = (d - k_diff + 26) % 26;
                        s_std += cnt_std * log_diff_prob[p_diff];
                    }
                }
                cost_kr[c1][c2][k_diff] = s_kr;
                cost_std[c1][c2][k_diff] = s_std;
            }
        }
    }

    printf("======================================================================\n");
    printf("Ultra-Fast 308.9M q7 State Sweep on RAW PK9 (%d pairs, 21 lookups/state)\n", n_pairs);
    printf("======================================================================\n");

    float base_ll = n_pairs * logf(1.0f / 26.0f);
    printf("Random Baseline LL = %.2f\n\n", base_ll);

    for (int mode = 0; mode < 2; mode++) {
        printf("Mode %d: %s\n", mode, mode == 0 ? "Quagmire III (Kryptos)" : "Standard Alphabet");
        double t0 = omp_get_wtime();

        float global_best_ll = -99999.0f;
        int best_q7[7];

        #pragma omp parallel
        {
            float loc_best_ll = -99999.0f;
            int loc_q7[7];

            #pragma omp for schedule(dynamic, 1)
            for (int k1 = 0; k1 < 26; k1++) {
                int q7[7];
                q7[0] = 0;
                q7[1] = k1;

                for (int k2 = 0; k2 < 26; k2++) {
                    q7[2] = k2;
                    for (int k3 = 0; k3 < 26; k3++) {
                        q7[3] = k3;
                        for (int k4 = 0; k4 < 26; k4++) {
                            q7[4] = k4;
                            for (int k5 = 0; k5 < 26; k5++) {
                                q7[5] = k5;
                                for (int k6 = 0; k6 < 26; k6++) {
                                    q7[6] = k6;

                                    float ll = 0.0f;
                                    if (mode == 0) {
                                        ll += cost_kr[0][1][(q7[1] - q7[0] + 26) % 26];
                                        ll += cost_kr[0][2][(q7[2] - q7[0] + 26) % 26];
                                        ll += cost_kr[0][3][(q7[3] - q7[0] + 26) % 26];
                                        ll += cost_kr[0][4][(q7[4] - q7[0] + 26) % 26];
                                        ll += cost_kr[0][5][(q7[5] - q7[0] + 26) % 26];
                                        ll += cost_kr[0][6][(q7[6] - q7[0] + 26) % 26];

                                        ll += cost_kr[1][2][(q7[2] - q7[1] + 26) % 26];
                                        ll += cost_kr[1][3][(q7[3] - q7[1] + 26) % 26];
                                        ll += cost_kr[1][4][(q7[4] - q7[1] + 26) % 26];
                                        ll += cost_kr[1][5][(q7[5] - q7[1] + 26) % 26];
                                        ll += cost_kr[1][6][(q7[6] - q7[1] + 26) % 26];

                                        ll += cost_kr[2][3][(q7[3] - q7[2] + 26) % 26];
                                        ll += cost_kr[2][4][(q7[4] - q7[2] + 26) % 26];
                                        ll += cost_kr[2][5][(q7[5] - q7[2] + 26) % 26];
                                        ll += cost_kr[2][6][(q7[6] - q7[2] + 26) % 26];

                                        ll += cost_kr[3][4][(q7[4] - q7[3] + 26) % 26];
                                        ll += cost_kr[3][5][(q7[5] - q7[3] + 26) % 26];
                                        ll += cost_kr[3][6][(q7[6] - q7[3] + 26) % 26];

                                        ll += cost_kr[4][5][(q7[5] - q7[4] + 26) % 26];
                                        ll += cost_kr[4][6][(q7[6] - q7[4] + 26) % 26];

                                        ll += cost_kr[5][6][(q7[6] - q7[5] + 26) % 26];
                                    } else {
                                        ll += cost_std[0][1][(q7[1] - q7[0] + 26) % 26];
                                        ll += cost_std[0][2][(q7[2] - q7[0] + 26) % 26];
                                        ll += cost_std[0][3][(q7[3] - q7[0] + 26) % 26];
                                        ll += cost_std[0][4][(q7[4] - q7[0] + 26) % 26];
                                        ll += cost_std[0][5][(q7[5] - q7[0] + 26) % 26];
                                        ll += cost_std[0][6][(q7[6] - q7[0] + 26) % 26];

                                        ll += cost_std[1][2][(q7[2] - q7[1] + 26) % 26];
                                        ll += cost_std[1][3][(q7[3] - q7[1] + 26) % 26];
                                        ll += cost_std[1][4][(q7[4] - q7[1] + 26) % 26];
                                        ll += cost_std[1][5][(q7[5] - q7[1] + 26) % 26];
                                        ll += cost_std[1][6][(q7[6] - q7[1] + 26) % 26];

                                        ll += cost_std[2][3][(q7[3] - q7[2] + 26) % 26];
                                        ll += cost_std[2][4][(q7[4] - q7[2] + 26) % 26];
                                        ll += cost_std[2][5][(q7[5] - q7[2] + 26) % 26];
                                        ll += cost_std[2][6][(q7[6] - q7[2] + 26) % 26];

                                        ll += cost_std[3][4][(q7[4] - q7[3] + 26) % 26];
                                        ll += cost_std[3][5][(q7[5] - q7[3] + 26) % 26];
                                        ll += cost_std[3][6][(q7[6] - q7[3] + 26) % 26];

                                        ll += cost_std[4][5][(q7[5] - q7[4] + 26) % 26];
                                        ll += cost_std[4][6][(q7[6] - q7[4] + 26) % 26];

                                        ll += cost_std[5][6][(q7[6] - q7[5] + 26) % 26];
                                    }

                                    if (ll > loc_best_ll) {
                                        loc_best_ll = ll;
                                        memcpy(loc_q7, q7, 7 * sizeof(int));
                                    }
                                }
                            }
                        }
                    }
                }
            }

            #pragma omp critical
            {
                if (loc_best_ll > global_best_ll) {
                    global_best_ll = loc_best_ll;
                    memcpy(best_q7, loc_q7, 7 * sizeof(int));
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        printf("Search of 308.9M q7 states completed in %.3f s (%.1f M states/sec)!\n",
               elapsed, 308.915776 / elapsed);
        printf("Best LL: %.2f (delta = %+.2f)\n", global_best_ll, global_best_ll - base_ll);
        printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n",
               best_q7[0], best_q7[1], best_q7[2], best_q7[3],
               best_q7[4], best_q7[5], best_q7[6]);
        printf("KR chars:  %c%c%c%c%c%c%c\n",
               KRYPTOS[best_q7[0]], KRYPTOS[best_q7[1]], KRYPTOS[best_q7[2]],
               KRYPTOS[best_q7[3]], KRYPTOS[best_q7[4]], KRYPTOS[best_q7[5]],
               KRYPTOS[best_q7[6]]);
        printf("STD chars: %c%c%c%c%c%c%c\n\n",
               'A' + best_q7[0], 'A' + best_q7[1], 'A' + best_q7[2],
               'A' + best_q7[3], 'A' + best_q7[4], 'A' + best_q7[5],
               'A' + best_q7[6]);
    }

    return 0;
}

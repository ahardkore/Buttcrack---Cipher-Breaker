#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";

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

    FILE *f = fopen("pk_all_ciphertexts.json", "r");
    if (!f) { printf("Cannot open json\n"); exit(1); }
    char buf[4096];
    size_t len = fread(buf, 1, sizeof(buf) - 1, f);
    buf[len] = '\0';
    fclose(f);

    char *p = strstr(buf, "\"PK10\": \"");
    p += 9;
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)p[i]];

    double p_k[26];
    for (int i = 0; i < 26; i++) p_k[i] = eng_freq[k2std[i]];

    double diff_dist[26] = {0};
    for (int a = 0; a < 26; a++) {
        for (int b = 0; b < 26; b++) {
            int d = (a - b + 26) % 26;
            diff_dist[d] += p_k[a] * p_k[b];
        }
    }
    for (int d = 0; d < 26; d++) log_diff_prob[d] = log(diff_dist[d]);
}

int main() {
    init_tables();

    printf("=======================================================\n");
    printf("PK10 CRT ISOLATION: TESTING CLOCK 7 AT STRIDE 72 MULTIPLES\n");
    printf("=======================================================\n");

    // Multiples of 72: 72, 144, 216, 288, 360, 432
    // 72 % 7 = 2
    // 144 % 7 = 4
    // 216 % 7 = 6
    // 288 % 7 = 1
    // 360 % 7 = 3
    // 432 % 7 = 5
    // ALL 6 NON-ZERO RESIDUES MOD 7 ARE COVERED!
    int strides[6] = {72, 144, 216, 288, 360, 432};
    int total_pairs = 0;

    // table_7[r][step_idx][dk]
    // r = t % 7 in {0..6}
    // step_idx in {0..5} corresponding to strides[0..5]
    // dk = shift difference in {0..25}
    double table_7[7][6][26] = {{{0}}};

    for (int s = 0; s < 6; s++) {
        int d = strides[s];
        int d_mod7 = d % 7;
        for (int t = 0; t < N - d; t++) {
            int r = t % 7;
            int cd = (ct_kr[t + d] - ct_kr[t] + 26) % 26;
            for (int dk = 0; dk < 26; dk++) {
                table_7[r][s][dk] += log_diff_prob[(cd - dk + 26) % 26];
            }
            total_pairs++;
        }
    }

    printf("Total isolated Stride-72 pairs for Clock 7: %d\n", total_pairs);
    double rand_baseline = total_pairs * log(1.0 / 26.0);
    printf("Random Baseline LL: %.2f\n\n", rand_baseline);

    double t0 = omp_get_wtime();
    double best_ll = -1e9;
    int best_q7[7] = {0};

    #pragma omp parallel
    {
        double loc_best_ll = -1e9;
        int loc_best_q7[7] = {0};

        #pragma omp for schedule(dynamic, 1)
        for (int q1 = 0; q1 < 26; q1++) {
            for (int q2 = 0; q2 < 26; q2++) {
                for (int q3 = 0; q3 < 26; q3++) {
                    for (int q4 = 0; q4 < 26; q4++) {
                        for (int q5 = 0; q5 < 26; q5++) {
                            for (int q6 = 0; q6 < 26; q6++) {
                                int q[7] = {0, q1, q2, q3, q4, q5, q6};

                                double ll = 0.0;
                                for (int r = 0; r < 7; r++) {
                                    for (int s = 0; s < 6; s++) {
                                        int d_mod7 = strides[s] % 7;
                                        int dk = (q[(r + d_mod7) % 7] - q[r] + 26) % 26;
                                        ll += table_7[r][s][dk];
                                    }
                                }

                                if (ll > loc_best_ll) {
                                    loc_best_ll = ll;
                                    for (int i = 0; i < 7; i++) loc_best_q7[i] = q[i];
                                }
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best_ll > best_ll) {
                best_ll = loc_best_ll;
                for (int i = 0; i < 7; i++) best_q7[i] = loc_best_q7[i];
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Sweep of all 308,915,776 q7 keys finished in %.3f s\n", elapsed);
    printf("Best Log-Likelihood: %.2f (vs baseline %.2f, delta = +%.2f)\n",
           best_ll, rand_baseline, best_ll - rand_baseline);
    printf("Recovered q7 vector: [%d, %d, %d, %d, %d, %d, %d]\n",
           best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
    printf("Letters in KRYPTOS: %c%c%c%c%c%c%c\n",
           KRYPTOS[best_q7[0]], KRYPTOS[best_q7[1]], KRYPTOS[best_q7[2]],
           KRYPTOS[best_q7[3]], KRYPTOS[best_q7[4]], KRYPTOS[best_q7[5]], KRYPTOS[best_q7[6]]);

    return 0;
}

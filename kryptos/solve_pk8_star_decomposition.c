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
static int k2std[26];

void init_tables() {
    int hpos[256];
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
    for (int d = 0; d < 26; d++) log_diff_prob[d] = log(diff_dist[d]);
}

// Data structures for the 3 star arms:
// Arm 7 (stride 30 multiples: 30, 60, 90, 120)
static int n30 = 0;
static int p30_t[350], p30_dt[350], p30_cd[350];

// Arm 6 (stride 35 multiples: 35, 70, 105, 140)
static int n35 = 0;
static int p35_t[350], p35_dt[350], p35_cd[350];

// Arm 5 (stride 42 multiples: 42, 84, 126)
static int n42 = 0;
static int p42_t[350], p42_dt[350], p42_cd[350];

void collect_pairs() {
    int s30[4] = {30, 60, 90, 120};
    for (int s = 0; s < 4; s++) {
        int d = s30[s];
        for (int t = 0; t < N - d; t++) {
            p30_t[n30] = t; p30_dt[n30] = d;
            p30_cd[n30] = (ct_kr[t + d] - ct_kr[t] + 26) % 26;
            n30++;
        }
    }

    int s35[4] = {35, 70, 105, 140};
    for (int s = 0; s < 4; s++) {
        int d = s35[s];
        for (int t = 0; t < N - d; t++) {
            p35_t[n35] = t; p35_dt[n35] = d;
            p35_cd[n35] = (ct_kr[t + d] - ct_kr[t] + 26) % 26;
            n35++;
        }
    }

    int s42[3] = {42, 84, 126};
    for (int s = 0; s < 3; s++) {
        int d = s42[s];
        for (int t = 0; t < N - d; t++) {
            p42_t[n42] = t; p42_dt[n42] = d;
            p42_cd[n42] = (ct_kr[t + d] - ct_kr[t] + 26) % 26;
            n42++;
        }
    }

    printf("Pairs collected: Arm7(30): %d, Arm6(35): %d, Arm5(42): %d | Total: %d\n",
           n30, n35, n42, n30 + n35 + n42);
}

typedef struct {
    double total_ll;
    double ll7, ll6, ll5;
    int q4[4], q5[5], q6[6], q7[7];
} StarSolution;

int main() {
    init_tables();
    collect_pairs();

    double rand_baseline = (n30 + n35 + n42) * log(1.0 / 26.0);
    printf("Random Baseline Total LL: %.2f\n\n", rand_baseline);

    double t0 = omp_get_wtime();

    #define KEEP_TOP 20
    StarSolution top_sols[KEEP_TOP];
    for (int i = 0; i < KEEP_TOP; i++) top_sols[i].total_ll = -1e9;

    printf("Executing Star-Decomposition Solver over all 17,576 q4 keys...\n");

    #pragma omp parallel
    {
        StarSolution loc_top[KEEP_TOP];
        for (int i = 0; i < KEEP_TOP; i++) loc_top[i].total_ll = -1e9;

        #pragma omp for schedule(dynamic, 64)
        for (int q4_idx = 0; q4_idx < 26 * 26 * 26; q4_idx++) {
            int q4[4];
            q4[0] = 0; // gauge
            q4[1] = q4_idx / (26 * 26);
            q4[2] = (q4_idx / 26) % 26;
            q4[3] = q4_idx % 26;

            // ----------------------------------------------------
            // ARM 7: Optimize q7 given q4 using n30 pairs
            // ----------------------------------------------------
            // Precompute histogram: for each r in {0..6} and d_q7 in {0..25}
            double tab7[7][26] = {{0}};
            for (int i = 0; i < n30; i++) {
                int t = p30_t[i];
                int d = p30_dt[i];
                int cd = p30_cd[i];
                int r = t % 7;
                int dq4 = (q4[(t + d) % 4] - q4[t % 4] + 26) % 26;
                int rem_cd = (cd - dq4 + 26) % 26;
                int d_stride_7 = d % 7; // 30%7=2, 60%7=4, 90%7=6, 120%7=1

                for (int v_from = 0; v_from < 26; v_from++) {
                    // We can optimize q7 coordinate-wise or test candidates
                }
            }

            // Since q7 has only 7 variables (gauge q7[0]=0 leaves 6 variables):
            // We can optimize q7 by coordinate descent in < 1 microsecond!
            int cur_q7[7] = {0};
            double best_ll7 = -1e9;
            for (int pass = 0; pass < 3; pass++) {
                for (int vi = 1; vi < 7; vi++) {
                    int best_v = cur_q7[vi];
                    for (int v = 0; v < 26; v++) {
                        cur_q7[vi] = v;
                        double ll = 0.0;
                        for (int i = 0; i < n30; i++) {
                            int t = p30_t[i];
                            int d = p30_dt[i];
                            int dk = (q4[(t + d) % 4] - q4[t % 4] + cur_q7[(t + d) % 7] - cur_q7[t % 7] + 52) % 26;
                            int dp = (p30_cd[i] - dk + 26) % 26;
                            ll += log_diff_prob[dp];
                        }
                        if (ll > best_ll7) { best_ll7 = ll; best_v = v; }
                    }
                    cur_q7[vi] = best_v;
                }
            }

            // ----------------------------------------------------
            // ARM 6: Optimize q6 given q4 using n35 pairs
            // ----------------------------------------------------
            int cur_q6[6] = {0};
            double best_ll6 = -1e9;
            for (int pass = 0; pass < 3; pass++) {
                for (int vi = 1; vi < 6; vi++) {
                    int best_v = cur_q6[vi];
                    for (int v = 0; v < 26; v++) {
                        cur_q6[vi] = v;
                        double ll = 0.0;
                        for (int i = 0; i < n35; i++) {
                            int t = p35_t[i];
                            int d = p35_dt[i];
                            int dk = (q4[(t + d) % 4] - q4[t % 4] + cur_q6[(t + d) % 6] - cur_q6[t % 6] + 52) % 26;
                            int dp = (p35_cd[i] - dk + 26) % 26;
                            ll += log_diff_prob[dp];
                        }
                        if (ll > best_ll6) { best_ll6 = ll; best_v = v; }
                    }
                    cur_q6[vi] = best_v;
                }
            }

            // ----------------------------------------------------
            // ARM 5: Optimize q5 given q4 using n42 pairs
            // ----------------------------------------------------
            int cur_q5[5] = {0};
            double best_ll5 = -1e9;
            for (int pass = 0; pass < 3; pass++) {
                for (int vi = 1; vi < 5; vi++) {
                    int best_v = cur_q5[vi];
                    for (int v = 0; v < 26; v++) {
                        cur_q5[vi] = v;
                        double ll = 0.0;
                        for (int i = 0; i < n42; i++) {
                            int t = p42_t[i];
                            int d = p42_dt[i];
                            int dk = (q4[(t + d) % 4] - q4[t % 4] + cur_q5[(t + d) % 5] - cur_q5[t % 5] + 52) % 26;
                            int dp = (p42_cd[i] - dk + 26) % 26;
                            ll += log_diff_prob[dp];
                        }
                        if (ll > best_ll5) { best_ll5 = ll; best_v = v; }
                    }
                    cur_q5[vi] = best_v;
                }
            }

            double total_ll = best_ll7 + best_ll6 + best_ll5;

            if (total_ll > loc_top[KEEP_TOP - 1].total_ll) {
                for (int i = 0; i < KEEP_TOP; i++) {
                    if (total_ll > loc_top[i].total_ll) {
                        for (int j = KEEP_TOP - 1; j > i; j--) loc_top[j] = loc_top[j - 1];
                        loc_top[i].total_ll = total_ll;
                        loc_top[i].ll7 = best_ll7;
                        loc_top[i].ll6 = best_ll6;
                        loc_top[i].ll5 = best_ll5;
                        memcpy(loc_top[i].q4, q4, 4 * sizeof(int));
                        memcpy(loc_top[i].q5, cur_q5, 5 * sizeof(int));
                        memcpy(loc_top[i].q6, cur_q6, 6 * sizeof(int));
                        memcpy(loc_top[i].q7, cur_q7, 7 * sizeof(int));
                        break;
                    }
                }
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < KEEP_TOP; i++) {
                double t_ll = loc_top[i].total_ll;
                if (t_ll > top_sols[KEEP_TOP - 1].total_ll) {
                    for (int j = 0; j < KEEP_TOP; j++) {
                        if (t_ll > top_sols[j].total_ll) {
                            for (int k = KEEP_TOP - 1; k > j; k--) top_sols[k] = top_sols[k - 1];
                            top_sols[j] = loc_top[i];
                            break;
                        }
                    }
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Star-Decomposition search finished in %.3f s\n\n", elapsed);

    printf("=== TOP 5 DECOUPLED CANDIDATE SOLUTIONS ===\n");
    for (int i = 0; i < 5; i++) {
        StarSolution *s = &top_sols[i];
        printf("Rank %d: Total LL = %.2f (vs baseline %.2f, delta = +%.2f)\n",
               i + 1, s->total_ll, rand_baseline, s->total_ll - rand_baseline);
        printf("  LL7 = %.2f, LL6 = %.2f, LL5 = %.2f\n", s->ll7, s->ll6, s->ll5);
        printf("  q4: [%d, %d, %d, %d] ('%c%c%c%c')\n",
               s->q4[0], s->q4[1], s->q4[2], s->q4[3],
               KRYPTOS[s->q4[0]], KRYPTOS[s->q4[1]], KRYPTOS[s->q4[2]], KRYPTOS[s->q4[3]]);
        printf("  q5: [%d, %d, %d, %d, %d] ('%c%c%c%c%c')\n",
               s->q5[0], s->q5[1], s->q5[2], s->q5[3], s->q5[4],
               KRYPTOS[s->q5[0]], KRYPTOS[s->q5[1]], KRYPTOS[s->q5[2]], KRYPTOS[s->q5[3]], KRYPTOS[s->q5[4]]);
        printf("  q6: [%d, %d, %d, %d, %d, %d] ('%c%c%c%c%c%c')\n",
               s->q6[0], s->q6[1], s->q6[2], s->q6[3], s->q6[4], s->q6[5],
               KRYPTOS[s->q6[0]], KRYPTOS[s->q6[1]], KRYPTOS[s->q6[2]], KRYPTOS[s->q6[3]], KRYPTOS[s->q6[4]], KRYPTOS[s->q6[5]]);
        printf("  q7: [%d, %d, %d, %d, %d, %d, %d] ('%c%c%c%c%c%c%c')\n",
               s->q7[0], s->q7[1], s->q7[2], s->q7[3], s->q7[4], s->q7[5], s->q7[6],
               KRYPTOS[s->q7[0]], KRYPTOS[s->q7[1]], KRYPTOS[s->q7[2]], KRYPTOS[s->q7[3]], KRYPTOS[s->q7[4]], KRYPTOS[s->q7[5]], KRYPTOS[s->q7[6]]);

        // Reconstruct plaintext
        char PT[N + 1];
        for (int t = 0; t < N; t++) {
            int k = (s->q4[t % 4] + s->q5[t % 5] + s->q6[t % 6] + s->q7[t % 7]) % 26;
            int p_kr = (ct_kr[t] - k + 26) % 26;
            PT[t] = 'A' + k2std[p_kr];
        }
        PT[N] = '\0';
        printf("  PT: %.70s...\n\n", PT);
    }

    return 0;
}

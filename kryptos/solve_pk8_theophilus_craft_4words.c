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
static int hpos[256];

void init_tables() {
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

static int n30 = 0, p30_t[350], p30_dt[350], p30_cd[350];
static int n35 = 0, p35_t[350], p35_dt[350], p35_cd[350];
static int n42 = 0, p42_t[350], p42_dt[350], p42_cd[350];

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
}

typedef struct {
    char str[12];
    int kr[8];
    int std[8];
} Word;

static Word *w4 = NULL; static int n4 = 0;
static Word *w5 = NULL; static int n5 = 0;
static Word *w6 = NULL; static int n6 = 0;
static Word *w7 = NULL; static int n7 = 0;

void load_word_file(const char *fn, Word **w_arr, int *n_arr, int len) {
    FILE *f = fopen(fn, "r");
    if (!f) { printf("Cannot open %s\n", fn); exit(1); }
    int cap = 2000;
    *w_arr = malloc(cap * sizeof(Word));
    *n_arr = 0;
    char buf[128];
    while (fscanf(f, "%127s", buf) == 1) {
        if (strlen(buf) == len) {
            Word *w = &(*w_arr)[*n_arr];
            strcpy(w->str, buf);
            for (int i = 0; i < len; i++) {
                w->std[i] = buf[i] - 'A';
                w->kr[i] = hpos[(unsigned char)buf[i]];
            }
            (*n_arr)++;
        }
    }
    fclose(f);
}

typedef struct {
    double total_ll;
    double ll7, ll6, ll5;
    char w4_str[8], w5_str[8], w6_str[8], w7_str[8];
} WordSolution;

int main() {
    init_tables();
    collect_pairs();

    load_word_file("theophilus_w4.txt", &w4, &n4, 4);
    load_word_file("theophilus_w5.txt", &w5, &n5, 5);
    load_word_file("theophilus_w6.txt", &w6, &n6, 6);
    load_word_file("theophilus_w7.txt", &w7, &n7, 7);
    printf("Loaded Theophilus craft words: W4=%d, W5=%d, W6=%d, W7=%d\n", n4, n5, n6, n7);

    double rand_baseline = (n30 + n35 + n42) * log(1.0 / 26.0);
    printf("Total orthogonal pairs: %d | Baseline LL: %.2f\n\n", n30 + n35 + n42, rand_baseline);

    for (int mode = 0; mode < 2; mode++) {
        printf("====================================================\n");
        printf("Testing Mode: %s\n", mode == 0 ? "Quagmire III (KRYPTOS)" : "Standard Alphabet");
        printf("====================================================\n");

        double t0 = omp_get_wtime();

        #define TOP_KEEP 10
        WordSolution top_sols[TOP_KEEP];
        for (int i = 0; i < TOP_KEEP; i++) top_sols[i].total_ll = -1e9;

        #pragma omp parallel
        {
            WordSolution loc_top[TOP_KEEP];
            for (int i = 0; i < TOP_KEEP; i++) loc_top[i].total_ll = -1e9;

            #pragma omp for schedule(dynamic, 16)
            for (int i4 = 0; i4 < n4; i4++) {
                const int *q4 = (mode == 0) ? w4[i4].kr : w4[i4].std;

                double tab7[7][4][26] = {{{0}}};
                for (int p = 0; p < n30; p++) {
                    int t = p30_t[p]; int d = p30_dt[p];
                    int r = t % 7;
                    int s_idx = (d == 30) ? 0 : ((d == 60) ? 1 : ((d == 90) ? 2 : 3));
                    int dq4 = (q4[(t + d) % 4] - q4[t % 4] + 26) % 26;
                    int rem_cd = (p30_cd[p] - dq4 + 26) % 26;
                    for (int dk7 = 0; dk7 < 26; dk7++) {
                        tab7[r][s_idx][dk7] += log_diff_prob[(rem_cd - dk7 + 26) % 26];
                    }
                }

                double tab6[6][4][26] = {{{0}}};
                for (int p = 0; p < n35; p++) {
                    int t = p35_t[p]; int d = p35_dt[p];
                    int r = t % 6;
                    int s_idx = (d == 35) ? 0 : ((d == 70) ? 1 : ((d == 105) ? 2 : 3));
                    int dq4 = (q4[(t + d) % 4] - q4[t % 4] + 26) % 26;
                    int rem_cd = (p35_cd[p] - dq4 + 26) % 26;
                    for (int dk6 = 0; dk6 < 26; dk6++) {
                        tab6[r][s_idx][dk6] += log_diff_prob[(rem_cd - dk6 + 26) % 26];
                    }
                }

                double tab5[5][3][26] = {{{0}}};
                for (int p = 0; p < n42; p++) {
                    int t = p42_t[p]; int d = p42_dt[p];
                    int r = t % 5;
                    int s_idx = (d == 42) ? 0 : ((d == 84) ? 1 : 2);
                    int dq4 = (q4[(t + d) % 4] - q4[t % 4] + 26) % 26;
                    int rem_cd = (p42_cd[p] - dq4 + 26) % 26;
                    for (int dk5 = 0; dk5 < 26; dk5++) {
                        tab5[r][s_idx][dk5] += log_diff_prob[(rem_cd - dk5 + 26) % 26];
                    }
                }

                // 1. Find best W7
                double best_ll7 = -1e9;
                int best_i7 = -1;
                static const int strides30[4] = {30, 60, 90, 120};
                for (int i7 = 0; i7 < n7; i7++) {
                    const int *q7 = (mode == 0) ? w7[i7].kr : w7[i7].std;
                    double ll = 0.0;
                    for (int r = 0; r < 7; r++) {
                        for (int s = 0; s < 4; s++) {
                            int d_mod7 = strides30[s] % 7;
                            int dk7 = (q7[(r + d_mod7) % 7] - q7[r] + 26) % 26;
                            ll += tab7[r][s][dk7];
                        }
                    }
                    if (ll > best_ll7) { best_ll7 = ll; best_i7 = i7; }
                }

                // 2. Find best W6
                double best_ll6 = -1e9;
                int best_i6 = -1;
                static const int strides35[4] = {35, 70, 105, 140};
                for (int i6 = 0; i6 < n6; i6++) {
                    const int *q6 = (mode == 0) ? w6[i6].kr : w6[i6].std;
                    double ll = 0.0;
                    for (int r = 0; r < 6; r++) {
                        for (int s = 0; s < 4; s++) {
                            int d_mod6 = strides35[s] % 6;
                            int dk6 = (q6[(r + d_mod6) % 6] - q6[r] + 26) % 26;
                            ll += tab6[r][s][dk6];
                        }
                    }
                    if (ll > best_ll6) { best_ll6 = ll; best_i6 = i6; }
                }

                // 3. Find best W5
                double best_ll5 = -1e9;
                int best_i5 = -1;
                static const int strides42[3] = {42, 84, 126};
                for (int i5 = 0; i5 < n5; i5++) {
                    const int *q5 = (mode == 0) ? w5[i5].kr : w5[i5].std;
                    double ll = 0.0;
                    for (int r = 0; r < 5; r++) {
                        for (int s = 0; s < 3; s++) {
                            int d_mod5 = strides42[s] % 5;
                            int dk5 = (q5[(r + d_mod5) % 5] - q5[r] + 26) % 26;
                            ll += tab5[r][s][dk5];
                        }
                    }
                    if (ll > best_ll5) { best_ll5 = ll; best_i5 = i5; }
                }

                double tot_ll = best_ll7 + best_ll6 + best_ll5;

                if (tot_ll > loc_top[TOP_KEEP - 1].total_ll) {
                    for (int k = 0; k < TOP_KEEP; k++) {
                        if (tot_ll > loc_top[k].total_ll) {
                            for (int j = TOP_KEEP - 1; j > k; j--) loc_top[j] = loc_top[j - 1];
                            loc_top[k].total_ll = tot_ll;
                            loc_top[k].ll7 = best_ll7;
                            loc_top[k].ll6 = best_ll6;
                            loc_top[k].ll5 = best_ll5;
                            strcpy(loc_top[k].w4_str, w4[i4].str);
                            strcpy(loc_top[k].w7_str, w7[best_i7].str);
                            strcpy(loc_top[k].w6_str, w6[best_i6].str);
                            strcpy(loc_top[k].w5_str, w5[best_i5].str);
                            break;
                        }
                    }
                }
            }

            #pragma omp critical
            {
                for (int k = 0; k < TOP_KEEP; k++) {
                    double t_ll = loc_top[k].total_ll;
                    if (t_ll > top_sols[TOP_KEEP - 1].total_ll) {
                        for (int j = 0; j < TOP_KEEP; j++) {
                            if (t_ll > top_sols[j].total_ll) {
                                for (int m = TOP_KEEP - 1; m > j; m--) top_sols[m] = top_sols[m - 1];
                                top_sols[j] = loc_top[k];
                                break;
                            }
                        }
                    }
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        printf("Search completed in %.3f s!\n\n", elapsed);

        printf("=== TOP 5 THEOPHILUS CRAFT WORD COMBINATIONS (Mode %d) ===\n", mode);
        for (int k = 0; k < 5; k++) {
            WordSolution *s = &top_sols[k];
            printf("Rank %d: Total LL = %.2f (delta = +%.2f)\n",
                   k + 1, s->total_ll, s->total_ll - rand_baseline);
            printf("  LL7 = %.2f, LL6 = %.2f, LL5 = %.2f\n", s->ll7, s->ll6, s->ll5);
            printf("  Words: W4: %s | W5: %s | W6: %s | W7: %s\n",
                   s->w4_str, s->w5_str, s->w6_str, s->w7_str);

            int q4[4], q5[5], q6[6], q7[7];
            for (int i = 0; i < 4; i++) q4[i] = (mode == 0) ? hpos[(unsigned char)s->w4_str[i]] : s->w4_str[i] - 'A';
            for (int i = 0; i < 5; i++) q5[i] = (mode == 0) ? hpos[(unsigned char)s->w5_str[i]] : s->w5_str[i] - 'A';
            for (int i = 0; i < 6; i++) q6[i] = (mode == 0) ? hpos[(unsigned char)s->w6_str[i]] : s->w6_str[i] - 'A';
            for (int i = 0; i < 7; i++) q7[i] = (mode == 0) ? hpos[(unsigned char)s->w7_str[i]] : s->w7_str[i] - 'A';

            char PT[N + 1];
            for (int t = 0; t < N; t++) {
                int k_sum = (q4[t % 4] + q5[t % 5] + q6[t % 6] + q7[t % 7]) % 26;
                int p_kr = (ct_kr[t] - k_sum + 26) % 26;
                PT[t] = 'A' + k2std[p_kr];
            }
            PT[N] = '\0';
            printf("  PT: %.70s...\n\n", PT);
        }
    }

    free(w4); free(w5); free(w6); free(w7);
    return 0;
}

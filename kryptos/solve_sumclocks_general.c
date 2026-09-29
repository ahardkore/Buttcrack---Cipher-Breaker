#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
static const char CT[N + 1] = "UQGIGYVYYCUIXEUUQGHWKVOWZEYCVWDUFUVUGBWZHYCGJWHGFLHETWDUWCCJGBWZHZCUFEEJGBNZHECUBEWXHCUECGVFEJHECCJGBWZGACURZWVFEJGBCUFBWZHFCLHETEZFVRGACUBEEJGBCUZGAY";
static const char KRYPTOS[27] = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char STD[27]     = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

// Quadgram table
static float quad[26][26][26][26];

void load_quadgrams(const char *path) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -10.0f;

    FILE *f = fopen(path, "r");
    if (!f) {
        printf("Failed to open %s\n", path);
        exit(1);
    }
    char line[128];
    double total = 0;
    long long counts[26][26][26][26] = {0};

    while (fgets(line, sizeof(line), f)) {
        char q[5];
        long long cnt;
        if (sscanf(line, "%4s %lld", q, &cnt) == 2) {
            int a = q[0] - 'A', b = q[1] - 'A', c = q[2] - 'A', d = q[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                counts[a][b][c][d] = cnt;
                total += cnt;
            }
        }
    }
    fclose(f);

    float log_tot = log10(total);
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    if (counts[a][b][c][d] > 0) {
                        quad[a][b][c][d] = log10((double)counts[a][b][c][d]) - log_tot;
                    } else {
                        quad[a][b][c][d] = -9.5f;
                    }
                }
}

// Coordinate descent for arbitrary set of periods
typedef struct {
    int num_clocks;
    int p[5];
} ClockConfig;

void test_clocks(ClockConfig cfg, const char *alph_name, int use_kryptos, int num_restarts) {
    int ct_idx[N];
    const char *ALPH = use_kryptos ? KRYPTOS : STD;
    for (int i = 0; i < N; i++) {
        const char *p = strchr(ALPH, CT[i]);
        ct_idx[i] = p ? (int)(p - ALPH) : 0;
    }

    printf("=== Testing clocks: ");
    for (int i = 0; i < cfg.num_clocks; i++) printf("%d ", cfg.p[i]);
    printf("on %s (%d restarts) ===\n", alph_name, num_restarts);

    float global_best_score = -9999.0f;
    int global_best_clocks[5][30];
    char global_best_pt[N + 1];

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 10007;
        float local_best_score = -9999.0f;
        int local_best_clocks[5][30];
        char local_best_pt[N + 1];

        #pragma omp for schedule(dynamic, 100)
        for (int restart = 0; restart < num_restarts; restart++) {
            int clk[5][30];
            for (int c = 0; c < cfg.num_clocks; c++) {
                for (int i = 0; i < cfg.p[c]; i++) {
                    clk[c][i] = rand_r(&seed) % 26;
                }
            }

            // Quick coordinate descent
            int pt_num[N];
            int changed = 1;
            int iter = 0;

            while (changed && iter < 10) {
                changed = 0;
                iter++;
                for (int c = 0; c < cfg.num_clocks; c++) {
                    for (int pos = 0; pos < cfg.p[c]; pos++) {
                        int best_shift = clk[c][pos];
                        float best_delta = 0.0f;

                        // Baseline score on affected quadgrams
                        // To be fast, recompute full text score
                        // (or just evaluate full text score since N=144 is tiny!)
                        // Let's do full text score for clarity and exactness:
                        for (int shift_try = 0; shift_try < 26; shift_try++) {
                            if (shift_try == clk[c][pos]) continue;
                            int old_s = clk[c][pos];
                            clk[c][pos] = shift_try;

                            for (int i = 0; i < N; i++) {
                                int sum_k = 0;
                                for (int k = 0; k < cfg.num_clocks; k++) sum_k += clk[k][i % cfg.p[k]];
                                int p = (ct_idx[i] - sum_k) % 26;
                                if (p < 0) p += 26;
                                pt_num[i] = use_kryptos ? (ALPH[p] - 'A') : p;
                            }

                            float cur_sc = 0;
                            for (int i = 0; i < N - 3; i++) {
                                cur_sc += quad[pt_num[i]][pt_num[i+1]][pt_num[i+2]][pt_num[i+3]];
                            }

                            // Restore
                            clk[c][pos] = old_s;

                            // We need to compare against baseline
                            // Let's compute baseline once per position
                        }
                    }
                }
            }
        }
    }
}

int main() {
    load_quadgrams("english_quadgrams.txt");
    printf("Quadgrams loaded.\n");
    return 0;
}

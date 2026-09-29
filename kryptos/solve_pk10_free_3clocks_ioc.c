#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504

static float uni_log[26];
static const float eng_freq[26] = {
    0.08167f, 0.01492f, 0.02782f, 0.04253f, 0.12702f, 0.02228f, 0.02015f, // A-G
    0.06094f, 0.06966f, 0.00153f, 0.00772f, 0.04025f, 0.02406f, 0.06749f, // H-N
    0.07507f, 0.01929f, 0.00095f, 0.05987f, 0.06327f, 0.09056f, 0.02758f, // O-U
    0.00978f, 0.02360f, 0.00150f, 0.01974f, 0.00074f                     // V-Z
};

void init_unigrams() {
    for (int i = 0; i < 26; i++) {
        uni_log[i] = logf(eng_freq[i]);
    }
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int c_idx[N];
static int alpha_to_std[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
    }
}

static inline float eval_all_clocks(const int *q7, const int *q8, const int *q9, float *out_ioc, int *out_counts) {
    int counts[26] = {0};
    float ll = 0.0f;

    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        int std_letter = alpha_to_std[p];
        counts[std_letter]++;
        ll += uni_log[std_letter];
    }

    int sum_pairs = 0;
    for (int i = 0; i < 26; i++) {
        sum_pairs += counts[i] * (counts[i] - 1);
    }
    float ioc = (float)sum_pairs / (N * (N - 1));

    if (out_ioc) *out_ioc = ioc;
    if (out_counts) memcpy(out_counts, counts, 26 * sizeof(int));

    int rare = counts[9] + counts[16] + counts[23] + counts[25]; // J, Q, X, Z
    float rare_pen = 0.0f;
    if (rare > 6) {
        rare_pen = (float)(rare - 6) * 20.0f;
    }

    // Combined score: unigram LL + IoC weighting - rare penalty
    return (ll / N) + (ioc * 25.0f) - (rare_pen / N);
}

int main(int argc, char **argv) {
    init_unigrams();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 50000;

    printf("======================================================================\n");
    printf("PK10 Fully Free 3-Clock Solver (Q7, Q8, Q9 all unconstrained)\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    float global_best_fitness = -999.0f;
    float global_best_ioc = 0.0f;
    int g_q7[7], g_q8[8], g_q9[9], g_counts[26];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 33333 + omp_get_thread_num() * 8819;
        float loc_best_fit = -999.0f;
        float loc_best_ioc = 0.0f;
        int l_q7[7], l_q8[8], l_q9[9], l_counts[26];

        #pragma omp for schedule(dynamic, 100)
        for (int rep = 0; rep < restarts; rep++) {
            int q7[7], q8[8], q9[9];
            q7[0] = 0;
            q8[0] = 0;
            for (int i = 1; i < 7; i++) q7[i] = rand_r(&seed) % 26;
            for (int i = 1; i < 8; i++) q8[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 9; i++) q9[i] = rand_r(&seed) % 26;

            float cur_ioc;
            float cur_fit = eval_all_clocks(q7, q8, q9, &cur_ioc, NULL);

            float temp = 1.0f;
            float cooling = 0.996f;

            for (int step = 0; step < 2500; step++) {
                int move = rand_r(&seed) % 22; // 6 in q7, 7 in q8, 9 in q9
                int old_v, new_v;

                if (move < 6) {
                    int pos = 1 + move;
                    old_v = q7[pos];
                    new_v = (old_v + 1 + rand_r(&seed) % 25) % 26;
                    q7[pos] = new_v;
                    float ioc;
                    float fit = eval_all_clocks(q7, q8, q9, &ioc, NULL);
                    float delta = fit - cur_fit;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_fit = fit; cur_ioc = ioc;
                    } else {
                        q7[pos] = old_v;
                    }
                } else if (move < 13) {
                    int pos = 1 + (move - 6);
                    old_v = q8[pos];
                    new_v = (old_v + 1 + rand_r(&seed) % 25) % 26;
                    q8[pos] = new_v;
                    float ioc;
                    float fit = eval_all_clocks(q7, q8, q9, &ioc, NULL);
                    float delta = fit - cur_fit;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_fit = fit; cur_ioc = ioc;
                    } else {
                        q8[pos] = old_v;
                    }
                } else {
                    int pos = move - 13;
                    old_v = q9[pos];
                    new_v = (old_v + 1 + rand_r(&seed) % 25) % 26;
                    q9[pos] = new_v;
                    float ioc;
                    float fit = eval_all_clocks(q7, q8, q9, &ioc, NULL);
                    float delta = fit - cur_fit;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_fit = fit; cur_ioc = ioc;
                    } else {
                        q9[pos] = old_v;
                    }
                }

                temp *= cooling;
            }

            // Polish coordinate descent
            int imp = 1;
            while (imp) {
                imp = 0;
                for (int pos = 1; pos < 7; pos++) {
                    int orig = q7[pos];
                    for (int cand = 0; cand < 26; cand++) {
                        if (cand == orig) continue;
                        q7[pos] = cand;
                        float ioc;
                        float fit = eval_all_clocks(q7, q8, q9, &ioc, NULL);
                        if (fit > cur_fit + 1e-4f) {
                            cur_fit = fit; cur_ioc = ioc; orig = cand; imp = 1;
                        }
                    }
                    q7[pos] = orig;
                }
                for (int pos = 1; pos < 8; pos++) {
                    int orig = q8[pos];
                    for (int cand = 0; cand < 26; cand++) {
                        if (cand == orig) continue;
                        q8[pos] = cand;
                        float ioc;
                        float fit = eval_all_clocks(q7, q8, q9, &ioc, NULL);
                        if (fit > cur_fit + 1e-4f) {
                            cur_fit = fit; cur_ioc = ioc; orig = cand; imp = 1;
                        }
                    }
                    q8[pos] = orig;
                }
                for (int pos = 0; pos < 9; pos++) {
                    int orig = q9[pos];
                    for (int cand = 0; cand < 26; cand++) {
                        if (cand == orig) continue;
                        q9[pos] = cand;
                        float ioc;
                        float fit = eval_all_clocks(q7, q8, q9, &ioc, NULL);
                        if (fit > cur_fit + 1e-4f) {
                            cur_fit = fit; cur_ioc = ioc; orig = cand; imp = 1;
                        }
                    }
                    q9[pos] = orig;
                }
            }

            if (cur_fit > loc_best_fit) {
                loc_best_fit = cur_fit;
                loc_best_ioc = cur_ioc;
                memcpy(l_q7, q7, 7 * sizeof(int));
                memcpy(l_q8, q8, 8 * sizeof(int));
                memcpy(l_q9, q9, 9 * sizeof(int));
                eval_all_clocks(q7, q8, q9, NULL, l_counts);
            }
        }

        #pragma omp critical
        {
            if (loc_best_fit > global_best_fitness) {
                global_best_fitness = loc_best_fit;
                global_best_ioc = loc_best_ioc;
                memcpy(g_q7, l_q7, 7 * sizeof(int));
                memcpy(g_q8, l_q8, 8 * sizeof(int));
                memcpy(g_q9, l_q9, 9 * sizeof(int));
                memcpy(g_counts, l_counts, 26 * sizeof(int));
                printf("[Thread %d] NEW RECORD: Fitness=%.4f, IoC=%.5f\n",
                       omp_get_thread_num(), global_best_fitness, global_best_ioc);
                printf("  Q7: [");
                for (int i = 0; i < 7; i++) printf("%d%s", g_q7[i], i==6?"":", ");
                printf("]\n  Q8: [");
                for (int i = 0; i < 8; i++) printf("%d%s", g_q8[i], i==7?"":", ");
                printf("]\n  Q9: [");
                for (int i = 0; i < 9; i++) printf("%d%s", g_q9[i], i==8?"":", ");
                printf("]\n  E count: %d (%.1f%%), Rare letters: %d (%.1f%%)\n\n",
                       g_counts['E'-'A'], (float)g_counts['E'-'A']/N*100.0f,
                       g_counts['J'-'A'] + g_counts['Q'-'A'] + g_counts['X'-'A'] + g_counts['Z'-'A'],
                       (float)(g_counts['J'-'A'] + g_counts['Q'-'A'] + g_counts['X'-'A'] + g_counts['Z'-'A'])/N*100.0f);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("ALL-CLOCKS SOLVER COMPLETED (%d restarts in %.3f s)\n", restarts, elapsed);
    printf("======================================================================\n");
    printf("Global Best Fitness: %.4f\n", global_best_fitness);
    printf("Global Best Monogram IoC: %.5f\n\n", global_best_ioc);
    printf("Q7 (len 7): [");
    for (int i = 0; i < 7; i++) printf("%d%s", g_q7[i], i==6?"":", ");
    printf("] (KR: ");
    for (int i = 0; i < 7; i++) printf("%c", KRYPTOS[g_q7[i]]);
    printf(")\n");
    printf("Q8 (len 8): [");
    for (int i = 0; i < 8; i++) printf("%d%s", g_q8[i], i==7?"":", ");
    printf("] (KR: ");
    for (int i = 0; i < 8; i++) printf("%c", KRYPTOS[g_q8[i]]);
    printf(")\n");
    printf("Q9 (len 9): [");
    for (int i = 0; i < 9; i++) printf("%d%s", g_q9[i], i==8?"":", ");
    printf("] (KR: ");
    for (int i = 0; i < 9; i++) printf("%c", KRYPTOS[g_q9[i]]);
    printf(")\n\n");

    printf("Letter Frequency Distribution in Intermediate Stream Z:\n");
    for (char c = 'A'; c <= 'Z'; c++) {
        int cnt = g_counts[c - 'A'];
        printf("  %c: %2d (%.1f%%)\n", c, cnt, (float)cnt / N * 100.0f);
    }

    return 0;
}

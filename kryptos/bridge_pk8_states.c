#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 153

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static float qtable[26][26][26][26];
static char valid_q[26][26][26][26];
static float unigram_logp[26];

static const float standard_unigrams[26] = {
    0.08167f, 0.01492f, 0.02782f, 0.04253f, 0.12702f, 0.02228f, 0.02015f,
    0.06094f, 0.06966f, 0.00153f, 0.00772f, 0.04025f, 0.02406f, 0.06749f,
    0.07507f, 0.01929f, 0.00095f, 0.05987f, 0.06327f, 0.09056f, 0.02758f,
    0.00978f, 0.02360f, 0.00150f, 0.01974f, 0.00074f
};

static void load_tables(void) {
    for (int i = 0; i < 26; i++) unigram_logp[i] = logf(standard_unigrams[i]);

    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    qtable[a][b][c][d] = -9.5f;
                    valid_q[a][b][c][d] = 0;
                }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) return;
    char buf[64];
    while (fgets(buf, sizeof(buf), f)) {
        char q[5]; float sc;
        if (sscanf(buf, "%4s %f", q, &sc) == 2) {
            int a = q[0] - 'A', b = q[1] - 'A', c = q[2] - 'A', d = q[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                qtable[a][b][c][d] = sc;
                valid_q[a][b][c][d] = 1;
            }
        }
    }
    fclose(f);
}

static inline void eval_pk8_hybrid(const int ct_kr[N], const int q4[4], const int q5[5], const int q6[6], const int q7[7],
                                  float *out_sc, int *out_def, float *out_ioc, int *out_rare, float *out_uni) {
    char pt[N];
    int counts[26] = {0};
    float uni = 0.0f;
    for (int i = 0; i < N; i++) {
        int shift = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
        int p_idx = (ct_kr[i] - shift + 26) % 26;
        char ch = KRYPTOS[p_idx];
        pt[i] = ch;
        counts[ch - 'A']++;
        uni += unigram_logp[ch - 'A'];
    }

    int sum_pairs = 0;
    for (int i = 0; i < 26; i++) sum_pairs += counts[i] * (counts[i] - 1);
    *out_ioc = (float)sum_pairs / (float)(N * (N - 1));
    *out_rare = counts['J'-'A'] + counts['Q'-'A'] + counts['X'-'A'] + counts['Z'-'A'];
    *out_uni = uni / (float)N;

    float sc = 0.0f;
    int def = 0;
    for (int i = 0; i < N - 3; i++) {
        int a = pt[i] - 'A', b = pt[i+1] - 'A', c = pt[i+2] - 'A', d = pt[i+3] - 'A';
        sc += qtable[a][b][c][d];
        if (!valid_q[a][b][c][d]) def++;
    }
    *out_sc = sc / (float)(N - 3);
    *out_def = def;
}

int main(void) {
    load_tables();

    int ct_kr[N];
    for (int i = 0; i < N; i++) ct_kr[i] = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;

    // State A (Quadgram/Lexical Champion):
    int stateA_q4[4] = {0, 6, 13, 20};
    int stateA_q5[5] = {3, 4, 15, 0, 10};
    int stateA_q6[6] = {3, 18, 15, 25, 20, 4};
    int stateA_q7[7] = {10, 2, 24, 0, 9, 5, 17};

    // State B (Stride Projection Champion):
    int stateB_q4[4] = {17, 1, 7, 22};
    int stateB_q5[5] = {0, 25, 12, 5, 18};
    int stateB_q6[6] = {0, 0, 8, 17, 10, 18};
    int stateB_q7[7] = {0, 19, 5, 9, 12, 4, 4};

    float scA, iocA, uniA; int defA, rareA;
    eval_pk8_hybrid(ct_kr, stateA_q4, stateA_q5, stateA_q6, stateA_q7, &scA, &defA, &iocA, &rareA, &uniA);

    float scB, iocB, uniB; int defB, rareB;
    eval_pk8_hybrid(ct_kr, stateB_q4, stateB_q5, stateB_q6, stateB_q7, &scB, &defB, &iocB, &rareB, &uniB);

    printf("======================================================================\n");
    printf("HYBRID BRIDGING & JOINT DESCENT ON PK8 (STATE A <-> STATE B)\n");
    printf("======================================================================\n");
    printf("State A Baseline: Score = %.4f | Defects = %d / 150 (%.1f%% valid) | IoC = %.5f | Rare = %d | Uni = %.2f\n",
           scA, defA, (150-defA)/150.0f*100.0f, iocA, rareA, uniA);
    printf("State B Baseline: Score = %.4f | Defects = %d / 150 (%.1f%% valid) | IoC = %.5f | Rare = %d | Uni = %.2f\n\n",
           scB, defB, (150-defB)/150.0f*100.0f, iocB, rareB, uniB);

    float global_best_sc = scA;
    int global_best_def = defA;
    int best_q4[4], best_q5[5], best_q6[6], best_q7[7];
    memcpy(best_q4, stateA_q4, sizeof(stateA_q4));
    memcpy(best_q5, stateA_q5, sizeof(stateA_q5));
    memcpy(best_q6, stateA_q6, sizeof(stateA_q6));
    memcpy(best_q7, stateA_q7, sizeof(stateA_q7));
    char best_pt[N + 1];

    int num_threads = omp_get_max_threads();
    printf("Executing 6,000,000 steps of hybrid simulated annealing across %d threads...\n", num_threads);

    #pragma omp parallel
    {
        unsigned int seed = 9999 + omp_get_thread_num() * 22223;
        int local_q4[4], local_q5[5], local_q6[6], local_q7[7];

        if (omp_get_thread_num() % 2 == 0) {
            memcpy(local_q4, stateA_q4, sizeof(stateA_q4));
            memcpy(local_q5, stateA_q5, sizeof(stateA_q5));
            memcpy(local_q6, stateA_q6, sizeof(stateA_q6));
            memcpy(local_q7, stateA_q7, sizeof(stateA_q7));
        } else {
            memcpy(local_q4, stateB_q4, sizeof(stateB_q4));
            memcpy(local_q5, stateB_q5, sizeof(stateB_q5));
            memcpy(local_q6, stateB_q6, sizeof(stateB_q6));
            memcpy(local_q7, stateB_q7, sizeof(stateB_q7));
        }

        float cur_sc, cur_ioc, cur_uni; int cur_def, cur_rare;
        eval_pk8_hybrid(ct_kr, local_q4, local_q5, local_q6, local_q7, &cur_sc, &cur_def, &cur_ioc, &cur_rare, &cur_uni);

        int steps = 3000000;
        float T_start = 0.5f, T_end = 0.0002f;

        for (int s = 0; s < steps; s++) {
            float frac = (float)s / steps;
            float T = T_start * powf(T_end / T_start, frac);

            int next_q4[4], next_q5[5], next_q6[6], next_q7[7];
            memcpy(next_q4, local_q4, sizeof(local_q4));
            memcpy(next_q5, local_q5, sizeof(local_q5));
            memcpy(next_q6, local_q6, sizeof(local_q6));
            memcpy(next_q7, local_q7, sizeof(local_q7));

            int m = rand_r(&seed) % 4;
            if (m == 0) {
                int idx = 1 + (rand_r(&seed) % 3);
                int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                next_q4[idx] = (next_q4[idx] + delta) % 26;
            } else if (m == 1) {
                int idx = rand_r(&seed) % 5;
                int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                next_q5[idx] = (next_q5[idx] + delta) % 26;
            } else if (m == 2) {
                int idx = rand_r(&seed) % 6;
                int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                next_q6[idx] = (next_q6[idx] + delta) % 26;
            } else {
                int idx = rand_r(&seed) % 7;
                int delta = (rand_r(&seed) % 2 == 0) ? 2 : 24;
                next_q7[idx] = (next_q7[idx] + delta) % 26;
            }

            float next_sc, next_ioc, next_uni; int next_def, next_rare;
            eval_pk8_hybrid(ct_kr, next_q4, next_q5, next_q6, next_q7, &next_sc, &next_def, &next_ioc, &next_rare, &next_uni);

            float cur_obj = (150 - cur_def) * 3.0f + cur_sc * 2.0f + cur_ioc * 25.0f + cur_uni * 5.0f - cur_rare * 0.2f;
            float next_obj = (150 - next_def) * 3.0f + next_sc * 2.0f + next_ioc * 25.0f + next_uni * 5.0f - next_rare * 0.2f;
            float d_fit = next_obj - cur_obj;

            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                memcpy(local_q4, next_q4, sizeof(local_q4));
                memcpy(local_q5, next_q5, sizeof(local_q5));
                memcpy(local_q6, next_q6, sizeof(local_q6));
                memcpy(local_q7, next_q7, sizeof(local_q7));
                cur_sc = next_sc; cur_def = next_def; cur_ioc = next_ioc; cur_rare = next_rare; cur_uni = next_uni;

                #pragma omp critical
                {
                    if (cur_def < global_best_def || (cur_def == global_best_def && cur_sc > global_best_sc)) {
                        global_best_def = cur_def;
                        global_best_sc = cur_sc;
                        memcpy(best_q4, local_q4, sizeof(local_q4));
                        memcpy(best_q5, local_q5, sizeof(local_q5));
                        memcpy(best_q6, local_q6, sizeof(local_q6));
                        memcpy(best_q7, local_q7, sizeof(local_q7));
                        for (int i = 0; i < N; i++) {
                            int shift = (best_q4[i%4] + best_q5[i%5] + best_q6[i%6] + best_q7[i%7]) % 26;
                            best_pt[i] = KRYPTOS[(ct_kr[i] - shift + 26) % 26];
                        }
                        best_pt[N] = '\0';
                        printf("[Thread %d | Step %d] NEW RECORD: Score = %.4f | Defects = %d / 150 (%.1f%% valid) | IoC = %.5f | Rare = %d\n",
                               omp_get_thread_num(), s, global_best_sc, global_best_def,
                               (150 - global_best_def)/150.0f * 100.0f, cur_ioc, cur_rare);
                        printf("  PT: %s\n\n", best_pt);
                    }
                }
            }
        }
    }

    printf("\n======================================================\n");
    printf("FINAL HYBRID BRIDGING RESULT FOR PK8:\n");
    printf("Score: %.4f | Defects: %d / 150 (%.1f%% valid)\n",
           global_best_sc, global_best_def, (150 - global_best_def)/150.0f * 100.0f);
    printf("Plaintext:\n%s\n", best_pt);
    printf("Q4: ["); for(int i=0;i<4;i++) printf("%d%s", best_q4[i], i==3?"":", "); printf("]\n");
    printf("Q5: ["); for(int i=0;i<5;i++) printf("%d%s", best_q5[i], i==4?"":", "); printf("]\n");
    printf("Q6: ["); for(int i=0;i<6;i++) printf("%d%s", best_q6[i], i==5?"":", "); printf("]\n");
    printf("Q7: ["); for(int i=0;i<7;i++) printf("%d%s", best_q7[i], i==6?"":", "); printf("]\n");

    return 0;
}

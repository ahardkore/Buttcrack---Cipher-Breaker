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

static void load_quads(void) {
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

static inline void eval_pk8_full(const int ct_kr[N], const int q4[4], const int q5[5], const int q6[6], const int q7[7],
                                 float *out_sc, int *out_def, float *out_ioc, int *out_rare) {
    char pt[N];
    int counts[26] = {0};
    for (int i = 0; i < N; i++) {
        int shift = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
        int p_idx = (ct_kr[i] - shift + 26) % 26;
        char ch = KRYPTOS[p_idx];
        pt[i] = ch;
        counts[ch - 'A']++;
    }

    int sum_pairs = 0;
    for (int i = 0; i < 26; i++) sum_pairs += counts[i] * (counts[i] - 1);
    *out_ioc = (float)sum_pairs / (float)(N * (N - 1));
    *out_rare = counts['J'-'A'] + counts['Q'-'A'] + counts['X'-'A'] + counts['Z'-'A'];

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
    load_quads();

    int ct_kr[N];
    for (int i = 0; i < N; i++) ct_kr[i] = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;

    // Proven Parity Vector for Q7
    int q7_parity[7] = {0, 1, 1, 1, 0, 0, 0};

    // Starting baseline from previous job
    int init_q4[4] = {0, 6, 13, 20};
    int init_q5[5] = {3, 4, 15, 0, 10};
    int init_q6[6] = {3, 18, 15, 25, 20, 4};
    int init_q7[7] = {10, 2, 24, 0, 9, 5, 17};

    float base_sc, base_ioc; int base_def, base_rare;
    eval_pk8_full(ct_kr, init_q4, init_q5, init_q6, init_q7, &base_sc, &base_def, &base_ioc, &base_rare);

    printf("======================================================================\n");
    printf("MASSIVE ALL-22 PARAMETER SIMULTANEOUS ANNEALER ON PK8\n");
    printf("======================================================================\n");
    printf("Initial State: Score = %.4f | Defects = %d / 150 (%.1f%% valid) | IoC = %.5f | Rare = %d\n\n",
           base_sc, base_def, (150 - base_def)/150.0f * 100.0f, base_ioc, base_rare);

    float global_best_sc = base_sc;
    int global_best_def = base_def;
    int best_q4[4], best_q5[5], best_q6[6], best_q7[7];
    memcpy(best_q4, init_q4, sizeof(init_q4));
    memcpy(best_q5, init_q5, sizeof(init_q5));
    memcpy(best_q6, init_q6, sizeof(init_q6));
    memcpy(best_q7, init_q7, sizeof(init_q7));
    char best_pt[N + 1];

    int num_threads = omp_get_max_threads();
    printf("Executing 10,000,000 steps across %d OpenMP threads...\n", num_threads);

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 37337;
        int local_q4[4], local_q5[5], local_q6[6], local_q7[7];
        memcpy(local_q4, init_q4, sizeof(init_q4));
        memcpy(local_q5, init_q5, sizeof(init_q5));
        memcpy(local_q6, init_q6, sizeof(init_q6));
        memcpy(local_q7, init_q7, sizeof(init_q7));

        if (omp_get_thread_num() > 0) {
            // slight random kick on initial state
            local_q5[rand_r(&seed) % 5] = rand_r(&seed) % 26;
            local_q6[rand_r(&seed) % 6] = rand_r(&seed) % 26;
        }

        float cur_sc, cur_ioc; int cur_def, cur_rare;
        eval_pk8_full(ct_kr, local_q4, local_q5, local_q6, local_q7, &cur_sc, &cur_def, &cur_ioc, &cur_rare);

        int steps = 5000000;
        float T_start = 0.6f, T_end = 0.0002f;

        for (int s = 0; s < steps; s++) {
            float frac = (float)s / steps;
            float T = T_start * powf(T_end / T_start, frac);

            int next_q4[4], next_q5[5], next_q6[6], next_q7[7];
            memcpy(next_q4, local_q4, sizeof(local_q4));
            memcpy(next_q5, local_q5, sizeof(local_q5));
            memcpy(next_q6, local_q6, sizeof(local_q6));
            memcpy(next_q7, local_q7, sizeof(local_q7));

            // Choose which clock to mutate (0: Q4, 1: Q5, 2: Q6, 3: Q7)
            int clock_choice = rand_r(&seed) % 4;

            if (clock_choice == 0) {
                // Mutate Q4 (fix q4[0]=0 as gauge)
                int idx = 1 + (rand_r(&seed) % 3);
                int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                next_q4[idx] = (next_q4[idx] + delta) % 26;
            } else if (clock_choice == 1) {
                // Mutate Q5
                int idx = rand_r(&seed) % 5;
                int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                next_q5[idx] = (next_q5[idx] + delta) % 26;
            } else if (clock_choice == 2) {
                // Mutate Q6
                int idx = rand_r(&seed) % 6;
                int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                next_q6[idx] = (next_q6[idx] + delta) % 26;
            } else {
                // Mutate Q7 (step by 2 to preserve binary parity!)
                int idx = rand_r(&seed) % 7;
                int delta = (rand_r(&seed) % 2 == 0) ? 2 : 24;
                next_q7[idx] = (next_q7[idx] + delta) % 26;
            }

            float next_sc, next_ioc; int next_def, next_rare;
            eval_pk8_full(ct_kr, next_q4, next_q5, next_q6, next_q7, &next_sc, &next_def, &next_ioc, &next_rare);

            // Objective: prioritize defect reduction, quadgrams, IoC, and suppress rare letters
            float cur_obj = (150 - cur_def) * 3.0f + cur_sc * 2.0f + cur_ioc * 20.0f - cur_rare * 0.15f;
            float next_obj = (150 - next_def) * 3.0f + next_sc * 2.0f + next_ioc * 20.0f - next_rare * 0.15f;
            float d_fit = next_obj - cur_obj;

            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                memcpy(local_q4, next_q4, sizeof(local_q4));
                memcpy(local_q5, next_q5, sizeof(local_q5));
                memcpy(local_q6, next_q6, sizeof(local_q6));
                memcpy(local_q7, next_q7, sizeof(local_q7));
                cur_sc = next_sc; cur_def = next_def; cur_ioc = next_ioc; cur_rare = next_rare;

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
                        printf("[Thread %d | Step %d] BREAKTHROUGH: Score = %.4f | Defects = %d / 150 (%.1f%% valid) | IoC = %.5f | Rare = %d\n",
                               omp_get_thread_num(), s, global_best_sc, global_best_def,
                               (150 - global_best_def)/150.0f * 100.0f, cur_ioc, cur_rare);
                        printf("  Plaintext: %s\n\n", best_pt);
                    }
                }
            }
        }
    }

    printf("\n======================================================\n");
    printf("FINAL ALL-22 PARAMETER PK8 BREAKING RESULT:\n");
    printf("Best Score: %.4f | Best Defects: %d / 150 (%.1f%% valid)\n",
           global_best_sc, global_best_def, (150 - global_best_def)/150.0f * 100.0f);
    printf("Plaintext:\n%s\n", best_pt);
    printf("Q4: ["); for(int i=0;i<4;i++) printf("%d%s", best_q4[i], i==3?"":", "); printf("]\n");
    printf("Q5: ["); for(int i=0;i<5;i++) printf("%d%s", best_q5[i], i==4?"":", "); printf("]\n");
    printf("Q6: ["); for(int i=0;i<6;i++) printf("%d%s", best_q6[i], i==5?"":", "); printf("]\n");
    printf("Q7: ["); for(int i=0;i<7;i++) printf("%d%s", best_q7[i], i==6?"":", "); printf("]\n");

    return 0;
}

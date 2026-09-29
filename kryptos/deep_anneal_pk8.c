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

static inline void eval_pk8(const int ct_kr[N], const int q4[4], const int q5[5], const int q6[6], const int q7[7],
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

    // Locked Q4: [0, 6, 13, 20] (Arithmetic Progression)
    int q4[4] = {0, 6, 13, 20};

    // Locked Q7: [10, 2, 24, 0, 9, 5, 17] (rot_4 of PK10's COLD LOCK)
    int q7[7] = {10, 2, 24, 0, 9, 5, 17};

    printf("======================================================================\n");
    printf("DEEP ANNEALING SOLVER ON PK8 (Q5, Q6) WITH LOCKED Q4 & Q7\n");
    printf("======================================================================\n");
    printf("Locked Q4: [0, 6, 13, 20] (Differences: +6, +7, +7, +6 = 26 mod 26)\n");
    printf("Locked Q7: [10, 2, 24, 0, 9, 5, 17] (rot_4 of PK10 COLD LOCK)\n\n");

    // Starting state from earlier run:
    int init_q5[5] = {3, 4, 15, 0, 10};
    int init_q6[6] = {3, 18, 15, 25, 20, 4};

    float base_sc, base_ioc; int base_def, base_rare;
    eval_pk8(ct_kr, q4, init_q5, init_q6, q7, &base_sc, &base_def, &base_ioc, &base_rare);
    printf("Initial Baseline: Score = %.4f | Defects = %d / 150 (%.1f%% valid) | IoC = %.5f | Rare = %d\n\n",
           base_sc, base_def, (150 - base_def)/150.0f * 100.0f, base_ioc, base_rare);

    float global_best_sc = base_sc;
    int global_best_def = base_def;
    int best_q5[5], best_q6[6];
    memcpy(best_q5, init_q5, sizeof(init_q5));
    memcpy(best_q6, init_q6, sizeof(init_q6));
    char best_pt[N + 1];

    int num_threads = omp_get_max_threads();
    printf("Running 5,000,000 deep annealing steps across %d threads...\n", num_threads);

    #pragma omp parallel
    {
        unsigned int seed = 8888 + omp_get_thread_num() * 19999;
        int local_q5[5], local_q6[6];
        memcpy(local_q5, init_q5, sizeof(init_q5));
        memcpy(local_q6, init_q6, sizeof(init_q6));

        // Add small random perturbation to explore multiple basins
        if (omp_get_thread_num() > 0) {
            local_q5[rand_r(&seed) % 5] = rand_r(&seed) % 26;
            local_q6[rand_r(&seed) % 6] = rand_r(&seed) % 26;
        }

        float cur_sc, cur_ioc; int cur_def, cur_rare;
        eval_pk8(ct_kr, q4, local_q5, local_q6, q7, &cur_sc, &cur_def, &cur_ioc, &cur_rare);

        int steps = 2500000;
        float T_start = 0.4f, T_end = 0.0005f;

        for (int s = 0; s < steps; s++) {
            float frac = (float)s / steps;
            float T = T_start * powf(T_end / T_start, frac);

            int next_q5[5], next_q6[6];
            memcpy(next_q5, local_q5, sizeof(local_q5));
            memcpy(next_q6, local_q6, sizeof(local_q6));

            if (rand_r(&seed) % 2 == 0) {
                int idx = rand_r(&seed) % 5;
                if (rand_r(&seed) % 2 == 0) next_q5[idx] = (next_q5[idx] + 1) % 26;
                else next_q5[idx] = (next_q5[idx] + 25) % 26;
            } else {
                int idx = rand_r(&seed) % 6;
                if (rand_r(&seed) % 2 == 0) next_q6[idx] = (next_q6[idx] + 1) % 26;
                else next_q6[idx] = (next_q6[idx] + 25) % 26;
            }

            float next_sc, next_ioc; int next_def, next_rare;
            eval_pk8(ct_kr, q4, next_q5, next_q6, q7, &next_sc, &next_def, &next_ioc, &next_rare);

            // Objective: prioritize reducing defects, maximizing quadgrams and IoC, penalizing rare letters
            float cur_obj = (150 - cur_def) * 2.0f + cur_sc * 1.5f + cur_ioc * 15.0f - cur_rare * 0.1f;
            float next_obj = (150 - next_def) * 2.0f + next_sc * 1.5f + next_ioc * 15.0f - next_rare * 0.1f;
            float d_fit = next_obj - cur_obj;

            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                memcpy(local_q5, next_q5, sizeof(local_q5));
                memcpy(local_q6, next_q6, sizeof(local_q6));
                cur_sc = next_sc; cur_def = next_def; cur_ioc = next_ioc; cur_rare = next_rare;

                #pragma omp critical
                {
                    if (cur_def < global_best_def || (cur_def == global_best_def && cur_sc > global_best_sc)) {
                        global_best_def = cur_def;
                        global_best_sc = cur_sc;
                        memcpy(best_q5, local_q5, sizeof(local_q5));
                        memcpy(best_q6, local_q6, sizeof(local_q6));
                        for (int i = 0; i < N; i++) {
                            int shift = (q4[i%4] + best_q5[i%5] + best_q6[i%6] + q7[i%7]) % 26;
                            best_pt[i] = KRYPTOS[(ct_kr[i] - shift + 26) % 26];
                        }
                        best_pt[N] = '\0';
                        printf("[Step %d] NEW BEST PK8: Score = %.4f | Defects = %d / 150 (%.1f%% valid) | IoC = %.5f | Rare = %d\n",
                               s, global_best_sc, global_best_def, (150 - global_best_def)/150.0f * 100.0f, cur_ioc, cur_rare);
                        printf("  PT: %s\n", best_pt);
                    }
                }
            }
        }
    }

    printf("\n======================================================\n");
    printf("FINAL DEEP ANNEALING PK8 CRACKING RESULT:\n");
    printf("Score: %.4f | Defects: %d / 150 (%.1f%% valid)\n",
           global_best_sc, global_best_def, (150 - global_best_def)/150.0f * 100.0f);
    printf("Full Plaintext:\n%s\n", best_pt);
    printf("Q4: [0, 6, 13, 20]\n");
    printf("Q5: ["); for(int i=0;i<5;i++) printf("%d%s", best_q5[i], i==4?"":", "); printf("]\n");
    printf("Q6: ["); for(int i=0;i<6;i++) printf("%d%s", best_q6[i], i==5?"":", "); printf("]\n");
    printf("Q7: [10, 2, 24, 0, 9, 5, 17]\n");

    return 0;
}

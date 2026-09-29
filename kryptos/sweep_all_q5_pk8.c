#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
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

int main(void) {
    load_quads();

    int ct_kr[N];
    for (int i = 0; i < N; i++) ct_kr[i] = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;

    int q4[4] = {0, 6, 13, 20};
    int q6[6] = {3, 18, 15, 25, 20, 4};
    int q7[7] = {10, 2, 24, 0, 9, 5, 17};

    // Precompute partial shifts: s_part[i] = q4[i%4] + q6[i%6] + q7[i%7] mod 26
    int s_part[N];
    for (int i = 0; i < N; i++) {
        s_part[i] = (q4[i % 4] + q6[i % 6] + q7[i % 7]) % 26;
    }

    printf("======================================================================\n");
    printf("EXHAUSTIVE EVALUATION OF ALL 26^5 = 11,881,376 Q5 STATES ON PK8\n");
    printf("======================================================================\n");

    int best_def = 999;
    float best_sc = -999.0f;
    int best_q5[5];
    char best_pt[N + 1];

    int num_threads = omp_get_max_threads();
    printf("Running on %d OpenMP threads...\n", num_threads);

    #pragma omp parallel
    {
        int loc_best_def = 999;
        float loc_best_sc = -999.0f;
        int loc_best_q5[5];
        char loc_best_pt[N + 1];

        #pragma omp for collapse(2) schedule(dynamic)
        for (int v0 = 0; v0 < 26; v0++) {
            for (int v1 = 0; v1 < 26; v1++) {
                int q5[5];
                q5[0] = v0; q5[1] = v1;

                for (int v2 = 0; v2 < 26; v2++) {
                    q5[2] = v2;
                    for (int v3 = 0; v3 < 26; v3++) {
                        q5[3] = v3;
                        for (int v4 = 0; v4 < 26; v4++) {
                            q5[4] = v4;

                            char pt[N];
                            for (int i = 0; i < N; i++) {
                                int shift = (s_part[i] + q5[i % 5]) % 26;
                                int p_idx = (ct_kr[i] - shift + 26) % 26;
                                pt[i] = KRYPTOS[p_idx];
                            }

                            float sc = 0.0f;
                            int def = 0;
                            for (int i = 0; i < N - 3; i++) {
                                int a = pt[i] - 'A', b = pt[i+1] - 'A', c = pt[i+2] - 'A', d = pt[i+3] - 'A';
                                sc += qtable[a][b][c][d];
                                if (!valid_q[a][b][c][d]) def++;
                            }
                            sc /= (float)(N - 3);

                            if (def < loc_best_def || (def == loc_best_def && sc > loc_best_sc)) {
                                loc_best_def = def;
                                loc_best_sc = sc;
                                memcpy(loc_best_q5, q5, sizeof(q5));
                                memcpy(loc_best_pt, pt, N);
                                loc_best_pt[N] = '\0';
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best_def < best_def || (loc_best_def == best_def && loc_best_sc > best_sc)) {
                best_def = loc_best_def;
                best_sc = loc_best_sc;
                memcpy(best_q5, loc_best_q5, sizeof(best_q5));
                memcpy(best_pt, loc_best_pt, N + 1);
                printf("[Thread %d] NEW BEST Q5: [%d, %d, %d, %d, %d] | Score = %.4f | Defects = %d / 150 (%.1f%% valid)\n",
                       omp_get_thread_num(), best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4],
                       best_sc, best_def, (150 - best_def)/150.0f * 100.0f);
                printf("  PT: %s\n\n", best_pt);
            }
        }
    }

    printf("\n======================================================\n");
    printf("EXHAUSTIVE Q5 EVALUATION COMPLETE:\n");
    printf("Global Optimal Q5: [%d, %d, %d, %d, %d]\n",
           best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4]);
    printf("Best Score: %.4f | Best Defects: %d / 150 (%.1f%% valid)\n",
           best_sc, best_def, (150 - best_def)/150.0f * 100.0f);
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}

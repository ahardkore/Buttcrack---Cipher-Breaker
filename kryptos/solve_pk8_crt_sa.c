#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
    char q[16]; float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const int q2_4[4] = {0, 1, 0, 0};
static const int q2_5[5] = {0, 0, 1, 0, 0};
static const int q2_6[6] = {0, 0, 0, 1, 0, 0};
static const int q2_7[7] = {0, 1, 1, 1, 0, 0, 0};

static inline int crt(int q2, int q13) {
    return (13 * q2 + 14 * q13) % 26;
}

int main(int argc, char **argv) {
    load_quadgrams();
    int N = strlen(PK8_CT);

    int c_idx[160];
    int alpha_to_std[26];
    for (int i = 0; i < 26; i++) alpha_to_std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;

    int num_restarts = 20000;
    if (argc > 1) num_restarts = atoi(argv[1]);

    printf("Starting Ultra-Fast OpenMP CRT SA + Descent on PK8 (%d restarts)...\n", num_restarts);

    float global_best_sc = -999.0f;
    char global_best_pt[160] = "";
    int best_q4[4], best_q5[5], best_q6[6], best_q7[7];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 10007;
        float local_best_sc = -999.0f;
        char local_best_pt[160] = "";
        int local_best_q4[4], local_best_q5[5], local_best_q6[6], local_best_q7[7];

        int pt[160];

        #pragma omp for schedule(dynamic, 50)
        for (int r = 0; r < num_restarts; r++) {
            int q13_4[4], q13_5[5], q13_6[6], q13_7[7];
            for (int i = 0; i < 4; i++) q13_4[i] = rand_r(&seed) % 13;
            for (int i = 0; i < 4; i++) q13_5[i] = rand_r(&seed) % 13; q13_5[4] = 0;
            for (int i = 0; i < 5; i++) q13_6[i] = rand_r(&seed) % 13; q13_6[5] = 0;
            for (int i = 0; i < 6; i++) q13_7[i] = rand_r(&seed) % 13; q13_7[6] = 0;

            int q4[4], q5[5], q6[6], q7[7];
            for (int i = 0; i < 4; i++) q4[i] = crt(q2_4[i], q13_4[i]);
            for (int i = 0; i < 5; i++) q5[i] = crt(q2_5[i], q13_5[i]);
            for (int i = 0; i < 6; i++) q6[i] = crt(q2_6[i], q13_6[i]);
            for (int i = 0; i < 7; i++) q7[i] = crt(q2_7[i], q13_7[i]);

            for (int i = 0; i < N; i++) {
                int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
            }
            float sc = 0;
            for (int i = 0; i < N - 3; i++) sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
            sc /= (N - 3);

            // Phase 1: Simulated Annealing (100 steps)
            float temp = 0.4f;
            float cool = 0.96f;
            for (int step = 0; step < 100; step++) {
                int clk = rand_r(&seed) % 4;
                int idx, old_v, new_v;
                if (clk == 0) {
                    idx = rand_r(&seed) % 4;
                    old_v = q13_4[idx];
                    new_v = rand_r(&seed) % 13;
                    if (new_v == old_v) continue;
                    q13_4[idx] = new_v;
                    q4[idx] = crt(q2_4[idx], new_v);
                } else if (clk == 1) {
                    idx = rand_r(&seed) % 4;
                    old_v = q13_5[idx];
                    new_v = rand_r(&seed) % 13;
                    if (new_v == old_v) continue;
                    q13_5[idx] = new_v;
                    q5[idx] = crt(q2_5[idx], new_v);
                } else if (clk == 2) {
                    idx = rand_r(&seed) % 5;
                    old_v = q13_6[idx];
                    new_v = rand_r(&seed) % 13;
                    if (new_v == old_v) continue;
                    q13_6[idx] = new_v;
                    q6[idx] = crt(q2_6[idx], new_v);
                } else {
                    idx = rand_r(&seed) % 6;
                    old_v = q13_7[idx];
                    new_v = rand_r(&seed) % 13;
                    if (new_v == old_v) continue;
                    q13_7[idx] = new_v;
                    q7[idx] = crt(q2_7[idx], new_v);
                }

                for (int i = 0; i < N; i++) {
                    int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                    pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                }
                float new_sc = 0;
                for (int i = 0; i < N - 3; i++) new_sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                new_sc /= (N - 3);

                float delta = new_sc - sc;
                if (delta > 0 || (temp > 0.001f && expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX))) {
                    sc = new_sc;
                } else {
                    // Revert
                    if (clk == 0) { q13_4[idx] = old_v; q4[idx] = crt(q2_4[idx], old_v); }
                    else if (clk == 1) { q13_5[idx] = old_v; q5[idx] = crt(q2_5[idx], old_v); }
                    else if (clk == 2) { q13_6[idx] = old_v; q6[idx] = crt(q2_6[idx], old_v); }
                    else { q13_7[idx] = old_v; q7[idx] = crt(q2_7[idx], old_v); }
                }
                temp *= cool;
            }

            // Phase 2: Greedy Coordinate Ascent
            int improved = 1;
            int iter = 0;
            while (improved && iter < 10) {
                improved = 0;
                iter++;

                // Clock 4
                for (int idx = 0; idx < 4; idx++) {
                    int best_v = q13_4[idx];
                    float best_sub = sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == q13_4[idx]) continue;
                        q4[idx] = crt(q2_4[idx], v);
                        float test_sc = 0;
                        for (int i = 0; i < N; i++) {
                            int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                            pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                        }
                        for (int i = 0; i < N - 3; i++) test_sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                        test_sc /= (N - 3);
                        if (test_sc > best_sub) { best_sub = test_sc; best_v = v; }
                    }
                    if (best_v != q13_4[idx]) {
                        q13_4[idx] = best_v;
                        q4[idx] = crt(q2_4[idx], best_v);
                        sc = best_sub;
                        improved = 1;
                    }
                }

                // Clock 5
                for (int idx = 0; idx < 4; idx++) {
                    int best_v = q13_5[idx];
                    float best_sub = sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == q13_5[idx]) continue;
                        q5[idx] = crt(q2_5[idx], v);
                        float test_sc = 0;
                        for (int i = 0; i < N; i++) {
                            int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                            pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                        }
                        for (int i = 0; i < N - 3; i++) test_sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                        test_sc /= (N - 3);
                        if (test_sc > best_sub) { best_sub = test_sc; best_v = v; }
                    }
                    if (best_v != q13_5[idx]) {
                        q13_5[idx] = best_v;
                        q5[idx] = crt(q2_5[idx], best_v);
                        sc = best_sub;
                        improved = 1;
                    }
                }

                // Clock 6
                for (int idx = 0; idx < 5; idx++) {
                    int best_v = q13_6[idx];
                    float best_sub = sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == q13_6[idx]) continue;
                        q6[idx] = crt(q2_6[idx], v);
                        float test_sc = 0;
                        for (int i = 0; i < N; i++) {
                            int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                            pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                        }
                        for (int i = 0; i < N - 3; i++) test_sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                        test_sc /= (N - 3);
                        if (test_sc > best_sub) { best_sub = test_sc; best_v = v; }
                    }
                    if (best_v != q13_6[idx]) {
                        q13_6[idx] = best_v;
                        q6[idx] = crt(q2_6[idx], best_v);
                        sc = best_sub;
                        improved = 1;
                    }
                }

                // Clock 7
                for (int idx = 0; idx < 6; idx++) {
                    int best_v = q13_7[idx];
                    float best_sub = sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == q13_7[idx]) continue;
                        q7[idx] = crt(q2_7[idx], v);
                        float test_sc = 0;
                        for (int i = 0; i < N; i++) {
                            int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                            pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                        }
                        for (int i = 0; i < N - 3; i++) test_sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                        test_sc /= (N - 3);
                        if (test_sc > best_sub) { best_sub = test_sc; best_v = v; }
                    }
                    if (best_v != q13_7[idx]) {
                        q13_7[idx] = best_v;
                        q7[idx] = crt(q2_7[idx], best_v);
                        sc = best_sub;
                        improved = 1;
                    }
                }
            }

            if (sc > local_best_sc) {
                local_best_sc = sc;
                for (int i = 0; i < 4; i++) local_best_q4[i] = q4[i];
                for (int i = 0; i < 5; i++) local_best_q5[i] = q5[i];
                for (int i = 0; i < 6; i++) local_best_q6[i] = q6[i];
                for (int i = 0; i < 7; i++) local_best_q7[i] = q7[i];
                for (int i = 0; i < N; i++) {
                    int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                    local_best_pt[i] = 'A' + alpha_to_std[(c_idx[i] - k + 26) % 26];
                }
                local_best_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                for (int i = 0; i < 4; i++) best_q4[i] = local_best_q4[i];
                for (int i = 0; i < 5; i++) best_q5[i] = local_best_q5[i];
                for (int i = 0; i < 6; i++) best_q6[i] = local_best_q6[i];
                for (int i = 0; i < 7; i++) best_q7[i] = local_best_q7[i];
                strcpy(global_best_pt, local_best_pt);

                printf("\n>>> CANDIDATE HIT! Score = %.4f (Native English: -4.3 to -4.5)\n", global_best_sc);
                printf("  q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
                printf("  q5: [%d, %d, %d, %d, %d]\n", best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4]);
                printf("  q6: [%d, %d, %d, %d, %d, %d]\n", best_q6[0], best_q6[1], best_q6[2], best_q6[3], best_q6[4], best_q6[5]);
                printf("  q7: [%d, %d, %d, %d, %d, %d, %d]\n", best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
                printf("  Plaintext: %.80s...\n\n", global_best_pt);
                fflush(stdout);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted %d restarts in %.2f s (%.1f restarts/sec)\n",
           num_restarts, elapsed, num_restarts / elapsed);
    printf("Global Best Quadgram Score = %.4f\n", global_best_sc);

    return 0;
}

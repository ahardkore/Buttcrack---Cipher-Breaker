#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const int q2_4[4] = {0, 1, 0, 0};
static const int q2_5[5] = {0, 0, 1, 0, 0};
static const int q2_6[6] = {0, 0, 0, 1, 0, 0};
static const int q2_7[7] = {0, 1, 1, 1, 0, 0, 0};

static inline int crt(int q2, int q13) {
    return (13 * q2 + 14 * q13) % 26;
}

static int c_idx[N];
static int alpha_to_std[26];
static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) exit(1);
    char q[16]; float sc;
    while (fscanf(f, "%s %f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;
    }
}

static inline float full_score(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s;
}

int main(int argc, char **argv) {
    init_tables();
    load_quadgrams();

    int restarts = 2000;
    if (argc > 1) restarts = atoi(argv[1]);

    printf("Starting Deep Fast SA on PK8 (%d restarts, 30,000 steps each)...\n", restarts);

    float global_best_sc = -99999.0f;
    int best_q4[4], best_q5[5], best_q6[6], best_q7[7];
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 54321 + omp_get_thread_num() * 99991;
        float local_best_sc = -99999.0f;
        int local_best_q4[4], local_best_q5[5], local_best_q6[6], local_best_q7[7];
        char local_best_pt[N + 1] = "";

        int pt[N];
        int q13_4[4], q13_5[5], q13_6[6], q13_7[7];
        int q4[4], q5[5], q6[6], q7[7];

        #pragma omp for schedule(dynamic, 1)
        for (int r = 0; r < restarts; r++) {
            // Random initialization of 19 free variables
            for (int i = 0; i < 4; i++) q13_4[i] = rand_r(&seed) % 13;
            for (int i = 0; i < 4; i++) q13_5[i] = rand_r(&seed) % 13; q13_5[4] = 0; // Gauge
            for (int i = 0; i < 5; i++) q13_6[i] = rand_r(&seed) % 13; q13_6[5] = 0; // Gauge
            for (int i = 0; i < 6; i++) q13_7[i] = rand_r(&seed) % 13; q13_7[6] = 0; // Gauge

            for (int i = 0; i < 4; i++) q4[i] = crt(q2_4[i], q13_4[i]);
            for (int i = 0; i < 5; i++) q5[i] = crt(q2_5[i], q13_5[i]);
            for (int i = 0; i < 6; i++) q6[i] = crt(q2_6[i], q13_6[i]);
            for (int i = 0; i < 7; i++) q7[i] = crt(q2_7[i], q13_7[i]);

            for (int i = 0; i < N; i++) {
                int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
            }

            float cur_sc = full_score(pt);

            // SA schedule
            float T = 10.0f;
            float T_end = 0.02f;
            int steps = 60000;
            float decay = powf(T_end / T, 1.0f / steps);

            for (int step = 0; step < steps; step++) {
                // Pick one of the 19 variables to mutate
                int var = rand_r(&seed) % 19;
                int clk, pos, period;
                if (var < 4) {
                    clk = 0; pos = var; period = 4;
                } else if (var < 8) {
                    clk = 1; pos = var - 4; period = 5;
                } else if (var < 13) {
                    clk = 2; pos = var - 8; period = 6;
                } else {
                    clk = 3; pos = var - 13; period = 7;
                }

                int old_v = (clk == 0) ? q13_4[pos] : ((clk == 1) ? q13_5[pos] : ((clk == 2) ? q13_6[pos] : q13_7[pos]));
                int new_v = (old_v + 1 + rand_r(&seed) % 12) % 13;

                int old_elem = (clk == 0) ? q4[pos] : ((clk == 1) ? q5[pos] : ((clk == 2) ? q6[pos] : q7[pos]));
                int par = (clk == 0) ? q2_4[pos] : ((clk == 1) ? q2_5[pos] : ((clk == 2) ? q2_6[pos] : q2_7[pos]));
                int new_elem = crt(par, new_v);

                // Compute delta quadgram score
                // Temporarily update elements and pt
                if (clk == 0) q4[pos] = new_elem;
                else if (clk == 1) q5[pos] = new_elem;
                else if (clk == 2) q6[pos] = new_elem;
                else q7[pos] = new_elem;

                float delta_sc = 0.0f;
                int saved_pt[60];
                int n_saved = 0;

                for (int i = pos; i < N; i += period) {
                    saved_pt[n_saved++] = pt[i];

                    int q_min = (i - 3 < 0) ? 0 : i - 3;
                    int q_max = (i > N - 4) ? N - 4 : i;
                    for (int q = q_min; q <= q_max; q++) {
                        delta_sc -= quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                    }

                    int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                    pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];

                    for (int q = q_min; q <= q_max; q++) {
                        delta_sc += quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                    }
                }

                if (delta_sc > 0 || (rand_r(&seed) / (float)RAND_MAX) < expf(delta_sc / T)) {
                    // Accept move
                    cur_sc += delta_sc;
                    if (clk == 0) q13_4[pos] = new_v;
                    else if (clk == 1) q13_5[pos] = new_v;
                    else if (clk == 2) q13_6[pos] = new_v;
                    else q13_7[pos] = new_v;
                } else {
                    // Reject: restore
                    if (clk == 0) q4[pos] = old_elem;
                    else if (clk == 1) q5[pos] = old_elem;
                    else if (clk == 2) q6[pos] = old_elem;
                    else q7[pos] = old_elem;

                    int idx = 0;
                    for (int i = pos; i < N; i += period) {
                        pt[i] = saved_pt[idx++];
                    }
                }

                T *= decay;
            }

            // Quench: Greedy coordinate descent
            int imp = 1;
            int passes = 0;
            while (imp && passes < 10) {
                imp = 0;
                passes++;
                for (int var = 0; var < 19; var++) {
                    int clk = (var < 4) ? 0 : ((var < 8) ? 1 : ((var < 13) ? 2 : 3));
                    int pos = (var < 4) ? var : ((var < 8) ? var - 4 : ((var < 13) ? var - 8 : var - 13));
                    int period = (clk == 0) ? 4 : ((clk == 1) ? 5 : ((clk == 2) ? 6 : 7));
                    int cur_v = (clk == 0) ? q13_4[pos] : ((clk == 1) ? q13_5[pos] : ((clk == 2) ? q13_6[pos] : q13_7[pos]));
                    int best_v = cur_v;
                    float best_d = 0.0f;

                    for (int test_v = 0; test_v < 13; test_v++) {
                        if (test_v == cur_v) continue;
                        int par = (clk == 0) ? q2_4[pos] : ((clk == 1) ? q2_5[pos] : ((clk == 2) ? q2_6[pos] : q2_7[pos]));
                        int test_elem = crt(par, test_v);

                        float d_sc = 0.0f;
                        int saved_pt[60];
                        int n_saved = 0;

                        if (clk == 0) q4[pos] = test_elem;
                        else if (clk == 1) q5[pos] = test_elem;
                        else if (clk == 2) q6[pos] = test_elem;
                        else q7[pos] = test_elem;

                        for (int i = pos; i < N; i += period) {
                            saved_pt[n_saved++] = pt[i];
                            int q_min = (i - 3 < 0) ? 0 : i - 3;
                            int q_max = (i > N - 4) ? N - 4 : i;
                            for (int q = q_min; q <= q_max; q++) d_sc -= quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                            int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                            pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                            for (int q = q_min; q <= q_max; q++) d_sc += quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                        }

                        // Restore pt
                        int old_elem = crt(par, cur_v);
                        if (clk == 0) q4[pos] = old_elem;
                        else if (clk == 1) q5[pos] = old_elem;
                        else if (clk == 2) q6[pos] = old_elem;
                        else q7[pos] = old_elem;

                        int idx = 0;
                        for (int i = pos; i < N; i += period) pt[i] = saved_pt[idx++];

                        if (d_sc > best_d) {
                            best_d = d_sc;
                            best_v = test_v;
                        }
                    }

                    if (best_v != cur_v) {
                        int par = (clk == 0) ? q2_4[pos] : ((clk == 1) ? q2_5[pos] : ((clk == 2) ? q2_6[pos] : q2_7[pos]));
                        int new_elem = crt(par, best_v);
                        if (clk == 0) { q13_4[pos] = best_v; q4[pos] = new_elem; }
                        else if (clk == 1) { q13_5[pos] = best_v; q5[pos] = new_elem; }
                        else if (clk == 2) { q13_6[pos] = best_v; q6[pos] = new_elem; }
                        else { q13_7[pos] = best_v; q7[pos] = new_elem; }

                        for (int i = pos; i < N; i += period) {
                            int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                            pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                        }
                        cur_sc += best_d;
                        imp = 1;
                    }
                }
            }

            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                for (int i = 0; i < 4; i++) local_best_q4[i] = q4[i];
                for (int i = 0; i < 5; i++) local_best_q5[i] = q5[i];
                for (int i = 0; i < 6; i++) local_best_q6[i] = q6[i];
                for (int i = 0; i < 7; i++) local_best_q7[i] = q7[i];
                for (int i = 0; i < N; i++) local_best_pt[i] = 'A' + pt[i];
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
                strcpy(best_pt, local_best_pt);

                float avg = global_best_sc / (N - 3);
                printf("\n>>> CANDIDATE HIT! Score = %.2f (avg = %.4f)\n", global_best_sc, avg);
                printf("  q4: ["); for (int i = 0; i < 4; i++) printf("%d%s", best_q4[i], i==3?"]\n":", ");
                printf("  q5: ["); for (int i = 0; i < 5; i++) printf("%d%s", best_q5[i], i==4?"]\n":", ");
                printf("  q6: ["); for (int i = 0; i < 6; i++) printf("%d%s", best_q6[i], i==5?"]\n":", ");
                printf("  q7: ["); for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6?"]\n":", ");
                printf("  Plaintext: %.120s...\n\n", best_pt);
                fflush(stdout);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished %d restarts (%.1f million steps) in %.2f s (%.1f restarts/sec)\n",
           restarts, (restarts * 30000.0) / 1e6, elapsed, restarts / elapsed);
    printf("Global Best Score = %.2f (avg = %.4f)\n", global_best_sc, global_best_sc / (N - 3));
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}

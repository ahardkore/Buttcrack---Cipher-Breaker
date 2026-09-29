#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

// Fixed Q4 and Q7 recovered from PK9
static const int q4_base[4] = {16, 23, 22, 18};
static const int q7_base[7] = {10, 19, 17, 25, 16, 18, 10};

// Universal binary parities
static const int q2_5[5] = {0, 0, 1, 0, 0};
static const int q2_6[6] = {0, 0, 0, 1, 0, 0};

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
    for (int i = 0; i < 26; i++) alpha_to_std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;
}

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    init_tables();
    load_quadgrams();

    printf("Solving PK8 via PK9 bridge with full 10 DOFs on (Q5, Q6) across all 28 rotations...\n");

    float global_best_sc = -999.0f;
    int best_rot4 = 0, best_rot7 = 0;
    int best_q5[5], best_q6[6];
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 10007;
        float local_best_sc = -999.0f;
        int local_best_rot4 = 0, local_best_rot7 = 0;
        int local_best_q5[5], local_best_q6[6];
        char local_best_pt[N + 1] = "";

        int pt[N];

        #pragma omp for schedule(dynamic, 1)
        for (int rot = 0; rot < 28; rot++) {
            int rot4 = rot % 4;
            int rot7 = rot / 4;

            int cur_q4[4], cur_q7[7];
            for (int i = 0; i < 4; i++) cur_q4[i] = q4_base[(i + rot4) % 4];
            for (int i = 0; i < 7; i++) cur_q7[i] = q7_base[(i + rot7) % 7];

            // 10 free variables: q13_5[0..4] (5 vars) + q13_6[0..4] (5 vars), q13_6[5] = 0 (gauge)
            for (int r = 0; r < 50; r++) {
                int q13_5[5], q13_6[6];
                for (int i = 0; i < 5; i++) q13_5[i] = rand_r(&seed) % 13;
                for (int i = 0; i < 5; i++) q13_6[i] = rand_r(&seed) % 13;
                q13_6[5] = 0; // Gauge

                int q5[5], q6[6];
                for (int i = 0; i < 5; i++) q5[i] = crt(q2_5[i], q13_5[i]);
                for (int i = 0; i < 6; i++) q6[i] = crt(q2_6[i], q13_6[i]);

                for (int i = 0; i < N; i++) {
                    int k = (cur_q4[i % 4] + q5[i % 5] + q6[i % 6] + cur_q7[i % 7]) % 26;
                    pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                }
                float cur_sc = score_plain(pt);

                float T = 8.0f;
                float T_end = 0.02f;
                int steps = 15000;
                float decay = powf(T_end / T, 1.0f / steps);

                for (int step = 0; step < steps; step++) {
                    int var = rand_r(&seed) % 10; // 5 for q5, 5 for q6
                    int clk = (var < 5) ? 0 : 1;
                    int pos = (var < 5) ? var : var - 5;
                    int period = (clk == 0) ? 5 : 6;

                    int old_v = (clk == 0) ? q13_5[pos] : q13_6[pos];
                    int new_v = (old_v + 1 + rand_r(&seed) % 12) % 13;
                    int par = (clk == 0) ? q2_5[pos] : q2_6[pos];
                    int new_elem = crt(par, new_v);
                    int old_elem = (clk == 0) ? q5[pos] : q6[pos];

                    if (clk == 0) q5[pos] = new_elem;
                    else q6[pos] = new_elem;

                    float delta_sc = 0.0f;
                    int saved[35];
                    int n_saved = 0;

                    for (int i = pos; i < N; i += period) {
                        saved[n_saved++] = pt[i];
                        int q_min = (i - 3 < 0) ? 0 : i - 3;
                        int q_max = (i > N - 4) ? N - 4 : i;
                        for (int q = q_min; q <= q_max; q++) delta_sc -= quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                        int k = (cur_q4[i % 4] + q5[i % 5] + q6[i % 6] + cur_q7[i % 7]) % 26;
                        pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                        for (int q = q_min; q <= q_max; q++) delta_sc += quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                    }

                    delta_sc /= (N - 3);

                    if (delta_sc > 0 || (rand_r(&seed) / (float)RAND_MAX) < expf(delta_sc / (T / (N - 3)))) {
                        cur_sc += delta_sc;
                        if (clk == 0) q13_5[pos] = new_v;
                        else q13_6[pos] = new_v;
                    } else {
                        // Revert
                        if (clk == 0) q5[pos] = old_elem;
                        else q6[pos] = old_elem;
                        int s_idx = 0;
                        for (int i = pos; i < N; i += period) pt[i] = saved[s_idx++];
                    }
                    T *= decay;
                }

                // Greedy polish
                int imp = 1;
                while (imp) {
                    imp = 0;
                    for (int var = 0; var < 10; var++) {
                        int clk = (var < 5) ? 0 : 1;
                        int pos = (var < 5) ? var : var - 5;
                        int period = (clk == 0) ? 5 : 6;
                        int cur_v = (clk == 0) ? q13_5[pos] : q13_6[pos];
                        int best_v = cur_v;
                        float best_d = 0.0f;

                        for (int test_v = 0; test_v < 13; test_v++) {
                            if (test_v == cur_v) continue;
                            int par = (clk == 0) ? q2_5[pos] : q2_6[pos];
                            int test_elem = crt(par, test_v);

                            if (clk == 0) q5[pos] = test_elem;
                            else q6[pos] = test_elem;

                            float d_sc = 0.0f;
                            int saved[35];
                            int n_saved = 0;

                            for (int i = pos; i < N; i += period) {
                                saved[n_saved++] = pt[i];
                                int q_min = (i - 3 < 0) ? 0 : i - 3;
                                int q_max = (i > N - 4) ? N - 4 : i;
                                for (int q = q_min; q <= q_max; q++) d_sc -= quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                                int k = (cur_q4[i % 4] + q5[i % 5] + q6[i % 6] + cur_q7[i % 7]) % 26;
                                pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                                for (int q = q_min; q <= q_max; q++) d_sc += quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                            }

                            d_sc /= (N - 3);

                            int old_elem = crt(par, cur_v);
                            if (clk == 0) q5[pos] = old_elem;
                            else q6[pos] = old_elem;
                            int s_idx = 0;
                            for (int i = pos; i < N; i += period) pt[i] = saved[s_idx++];

                            if (d_sc > best_d) {
                                best_d = d_sc;
                                best_v = test_v;
                            }
                        }

                        if (best_v != cur_v) {
                            int par = (clk == 0) ? q2_5[pos] : q2_6[pos];
                            int new_elem = crt(par, best_v);
                            if (clk == 0) { q13_5[pos] = best_v; q5[pos] = new_elem; }
                            else { q13_6[pos] = best_v; q6[pos] = new_elem; }
                            for (int i = pos; i < N; i += period) {
                                int k = (cur_q4[i % 4] + q5[i % 5] + q6[i % 6] + cur_q7[i % 7]) % 26;
                                pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                            }
                            cur_sc += best_d;
                            imp = 1;
                        }
                    }
                }

                if (cur_sc > local_best_sc) {
                    local_best_sc = cur_sc;
                    local_best_rot4 = rot4;
                    local_best_rot7 = rot7;
                    for (int i = 0; i < 5; i++) local_best_q5[i] = q5[i];
                    for (int i = 0; i < 6; i++) local_best_q6[i] = q6[i];
                    for (int i = 0; i < N; i++) local_best_pt[i] = 'A' + pt[i];
                    local_best_pt[N] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                best_rot4 = local_best_rot4;
                best_rot7 = local_best_rot7;
                for (int i = 0; i < 5; i++) best_q5[i] = local_best_q5[i];
                for (int i = 0; i < 6; i++) best_q6[i] = local_best_q6[i];
                strcpy(best_pt, local_best_pt);

                printf("\n>>> CANDIDATE HIT! Score = %.4f | rot4=%d, rot7=%d\n",
                       global_best_sc, best_rot4, best_rot7);
                printf("  q5: ["); for (int i = 0; i < 5; i++) printf("%d%s", best_q5[i], i==4?"]\n":", ");
                printf("  q6: ["); for (int i = 0; i < 6; i++) printf("%d%s", best_q6[i], i==5?"]\n":", ");
                printf("  Plaintext: %.120s...\n\n", best_pt);
                fflush(stdout);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\n=== SEARCH COMPLETE in %.2f s ===\n", elapsed);
    printf("Global Best Score = %.4f | rot4=%d, rot7=%d\n", global_best_sc, best_rot4, best_rot7);
    printf("q5: ["); for (int i = 0; i < 5; i++) printf("%d%s", best_q5[i], i==4?"]\n":", ");
    printf("q6: ["); for (int i = 0; i < 6; i++) printf("%d%s", best_q6[i], i==5?"]\n":", ");
    printf("Plaintext: %s\n", best_pt);

    FILE *fout = fopen("pk8_solution_pt.txt", "w");
    if (fout) {
        fprintf(fout, "Score: %.4f\nRot4: %d, Rot7: %d\n%s\n", global_best_sc, best_rot4, best_rot7, best_pt);
        fclose(fout);
    }
    return 0;
}

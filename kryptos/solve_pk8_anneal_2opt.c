#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 153
#define NUM_VARS 22

static float quad[26][26][26][26];

void load_quads() {
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

static int ct_kr[N];
static int k2std[26];
static int hpos[256];

static inline float score_pt(const int *pt_std) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return s / (N - 3);
}

void compute_pt(const int *vars, int *pt_std) {
    for (int t = 0; t < N; t++) {
        int k = (vars[t % 4] + vars[4 + (t % 5)] + vars[9 + (t % 6)] + vars[15 + (t % 7)]) % 26;
        int p_kr = (ct_kr[t] - k + 26) % 26;
        pt_std[t] = k2std[p_kr];
    }
}

// Full Hybrid: SA -> 1-Opt -> 2-Opt
float hybrid_solve(int *vars, unsigned int *seed) {
    int pt_std[N];
    compute_pt(vars, pt_std);
    float cur_sc = score_pt(pt_std);

    // Stage 1: Fast Annealing (3,000 steps)
    float T = 2.0f;
    float cooling = 0.999f;
    for (int step = 0; step < 3000; step++) {
        T *= cooling;
        int vi = rand_r(seed) % NUM_VARS;
        if (vi == 0 || vi == 4 || vi == 9 || vi == 15) continue; // fix gauges

        int old_v = vars[vi];
        int new_v = (old_v + 1 + rand_r(seed) % 25) % 26;
        vars[vi] = new_v;

        compute_pt(vars, pt_std);
        float new_sc = score_pt(pt_std);
        float delta = new_sc - cur_sc;

        if (delta > 0 || (float)rand_r(seed) / RAND_MAX < expf(delta / T)) {
            cur_sc = new_sc;
        } else {
            vars[vi] = old_v;
        }
    }

    // Stage 2: 1-Opt Greedy Polish
    int improved = 1;
    int passes = 0;
    while (improved && passes < 10) {
        improved = 0;
        passes++;
        for (int vi = 0; vi < NUM_VARS; vi++) {
            if (vi == 0 || vi == 4 || vi == 9 || vi == 15) continue;
            int old_v = vars[vi];
            int best_v = old_v;
            float best_s = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == old_v) continue;
                vars[vi] = v;
                compute_pt(vars, pt_std);
                float sc = score_pt(pt_std);
                if (sc > best_s) {
                    best_s = sc;
                    best_v = v;
                }
            }
            vars[vi] = best_v;
            if (best_v != old_v) {
                cur_sc = best_s;
                improved = 1;
            }
        }
    }

    // Stage 3: 2-Opt Coupled Polish
    improved = 1;
    passes = 0;
    while (improved && passes < 6) {
        improved = 0;
        passes++;
        for (int v1 = 0; v1 < NUM_VARS - 1; v1++) {
            if (v1 == 0 || v1 == 4 || v1 == 9 || v1 == 15) continue;
            for (int v2 = v1 + 1; v2 < NUM_VARS; v2++) {
                if (v2 == 0 || v2 == 4 || v2 == 9 || v2 == 15) continue;

                int old_v1 = vars[v1];
                int old_v2 = vars[v2];
                int best_d = 0;
                float best_s = cur_sc;

                for (int d = 1; d < 26; d++) {
                    vars[v1] = (old_v1 + d) % 26;
                    vars[v2] = (old_v2 - d + 26) % 26;
                    compute_pt(vars, pt_std);
                    float sc = score_pt(pt_std);
                    if (sc > best_s) {
                        best_s = sc;
                        best_d = d;
                    }
                }
                if (best_d != 0) {
                    vars[v1] = (old_v1 + best_d) % 26;
                    vars[v2] = (old_v2 - best_d + 26) % 26;
                    cur_sc = best_s;
                    improved = 1;
                } else {
                    vars[v1] = old_v1;
                    vars[v2] = old_v2;
                }
            }
        }
    }

    return cur_sc;
}

int main() {
    load_quads();

    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK8_CT[i]];

    printf("Starting Hybrid SA + 1-Opt + 2-Opt Solver on PK8...\n");
    double t0 = omp_get_wtime();

    float global_best_sc = -999.0f;
    char global_best_pt[160] = "";
    int best_vars[NUM_VARS];

    #define TOTAL_RESTARTS 10000

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_best_pt[160] = "";
        int loc_vars[NUM_VARS];
        unsigned int seed = 77777 + omp_get_thread_num() * 12345;

        #pragma omp for schedule(dynamic, 10)
        for (int r = 0; r < TOTAL_RESTARTS; r++) {
            int cur_vars[NUM_VARS];
            for (int i = 0; i < NUM_VARS; i++) {
                if (i == 0 || i == 4 || i == 9 || i == 15) cur_vars[i] = 0;
                else cur_vars[i] = rand_r(&seed) % 26;
            }

            float sc = hybrid_solve(cur_vars, &seed);

            if (sc > -5.8f) {
                #pragma omp critical
                {
                    int pt_std[N];
                    compute_pt(cur_vars, pt_std);
                    char pt_str[N + 1];
                    for (int t = 0; t < N; t++) pt_str[t] = 'A' + pt_std[t];
                    pt_str[N] = '\0';
                    printf(">>> BREAKTHROUGH HIT! Score: %.4f <<<\n", sc);
                    printf("  PT: %s\n\n", pt_str);
                }
            }

            if (sc > local_best_sc) {
                local_best_sc = sc;
                memcpy(loc_vars, cur_vars, NUM_VARS * sizeof(int));
                int pt_std[N];
                compute_pt(cur_vars, pt_std);
                for (int t = 0; t < N; t++) local_best_pt[t] = 'A' + pt_std[t];
                local_best_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                memcpy(best_vars, loc_vars, NUM_VARS * sizeof(int));
                strcpy(global_best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed %d hybrid restarts in %.3f seconds!\n", TOTAL_RESTARTS, elapsed);
    printf("Global Best Score: %.4f\n", global_best_sc);
    printf("q4: [%d, %d, %d, %d]\n", best_vars[0], best_vars[1], best_vars[2], best_vars[3]);
    printf("q5: [%d, %d, %d, %d, %d]\n", best_vars[4], best_vars[5], best_vars[6], best_vars[7], best_vars[8]);
    printf("q6: [%d, %d, %d, %d, %d, %d]\n", best_vars[9], best_vars[10], best_vars[11], best_vars[12], best_vars[13], best_vars[14]);
    printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n", best_vars[15], best_vars[16], best_vars[17], best_vars[18], best_vars[19], best_vars[20], best_vars[21]);
    printf("PT: %s\n", global_best_pt);

    return 0;
}

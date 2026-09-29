#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 153

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

int main() {
    load_quads();

    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK8_CT[i]];

    // Mask 116: q7 = [0, 2, 22, 10, 23, 19, 20] ('KYVDWNQ')
    int q7_base[7] = {0, 2, 22, 10, 23, 19, 20};

    printf("Starting 12-Variable Simulated Annealing on PK8 (q7 fixed to Mask 116)...\n");
    double t0 = omp_get_wtime();

    float global_best_sc = -999.0f;
    char global_best_pt[160] = "";
    int best_q4[4], best_q5[5], best_q6[6], best_q7[7];

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_best_pt[160] = "";
        int loc_q4[4], loc_q5[5], loc_q6[6], loc_q7[7];
        unsigned int seed = 54321 + omp_get_thread_num() * 11003;

        #pragma omp for schedule(dynamic, 1)
        for (int phase = 0; phase < 7; phase++) {
            int q7[7];
            for (int j = 0; j < 7; j++) q7[j] = q7_base[(j + phase) % 7];

            // 500 restarts per phase
            for (int restart = 0; restart < 500; restart++) {
                int q4[4] = {0, rand_r(&seed) % 26, rand_r(&seed) % 26, rand_r(&seed) % 26};
                int q5[5] = {0, rand_r(&seed) % 26, rand_r(&seed) % 26, rand_r(&seed) % 26, rand_r(&seed) % 26};
                int q6[6] = {0, rand_r(&seed) % 26, rand_r(&seed) % 26, rand_r(&seed) % 26, rand_r(&seed) % 26, rand_r(&seed) % 26};

                int pt_kr[N], pt_std[N];
                for (int t = 0; t < N; t++) {
                    int k = (q4[t % 4] + q5[t % 5] + q6[t % 6] + q7[t % 7]) % 26;
                    pt_kr[t] = (ct_kr[t] - k + 26) % 26;
                    pt_std[t] = k2std[pt_kr[t]];
                }
                float cur_sc = score_pt(pt_std);

                float T = 2.0f;
                float cooling = 0.9995f;

                for (int step = 0; step < 15000; step++) {
                    T *= cooling;

                    // Choose variable to mutate: 3 from q4 (1..3), 4 from q5 (1..4), 5 from q6 (1..5)
                    // Total 12 variables
                    int var_idx = rand_r(&seed) % 12;
                    int old_val;
                    int *target;
                    int clock_type; // 4, 5, or 6
                    int clock_rem;

                    if (var_idx < 3) {
                        clock_type = 4;
                        clock_rem = var_idx + 1;
                        target = &q4[clock_rem];
                    } else if (var_idx < 7) {
                        clock_type = 5;
                        clock_rem = var_idx - 3 + 1;
                        target = &q5[clock_rem];
                    } else {
                        clock_type = 6;
                        clock_rem = var_idx - 7 + 1;
                        target = &q6[clock_rem];
                    }

                    old_val = *target;
                    int new_val = (old_val + 1 + rand_r(&seed) % 25) % 26;
                    *target = new_val;

                    // Update plaintext at affected positions
                    for (int t = clock_rem; t < N; t += clock_type) {
                        int k = (q4[t % 4] + q5[t % 5] + q6[t % 6] + q7[t % 7]) % 26;
                        pt_kr[t] = (ct_kr[t] - k + 26) % 26;
                        pt_std[t] = k2std[pt_kr[t]];
                    }

                    float new_sc = score_pt(pt_std);
                    float delta = new_sc - cur_sc;

                    if (delta > 0 || (float)rand_r(&seed) / RAND_MAX < expf(delta / T)) {
                        cur_sc = new_sc;
                        if (cur_sc > local_best_sc) {
                            local_best_sc = cur_sc;
                            memcpy(loc_q4, q4, 4 * sizeof(int));
                            memcpy(loc_q5, q5, 5 * sizeof(int));
                            memcpy(loc_q6, q6, 6 * sizeof(int));
                            memcpy(loc_q7, q7, 7 * sizeof(int));
                            for (int t = 0; t < N; t++) local_best_pt[t] = 'A' + pt_std[t];
                            local_best_pt[N] = '\0';
                        }
                    } else {
                        // Revert
                        *target = old_val;
                        for (int t = clock_rem; t < N; t += clock_type) {
                            int k = (q4[t % 4] + q5[t % 5] + q6[t % 6] + q7[t % 7]) % 26;
                            pt_kr[t] = (ct_kr[t] - k + 26) % 26;
                            pt_std[t] = k2std[pt_kr[t]];
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                memcpy(best_q4, loc_q4, 4 * sizeof(int));
                memcpy(best_q5, loc_q5, 5 * sizeof(int));
                memcpy(best_q6, loc_q6, 6 * sizeof(int));
                memcpy(best_q7, loc_q7, 7 * sizeof(int));
                strcpy(global_best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Annealing completed in %.3f seconds!\n", elapsed);
    printf("Global Best Score: %.4f\n", global_best_sc);
    printf("q4: [%d, %d, %d, %d] ('%c%c%c%c')\n",
           best_q4[0], best_q4[1], best_q4[2], best_q4[3],
           KRYPTOS[best_q4[0]], KRYPTOS[best_q4[1]], KRYPTOS[best_q4[2]], KRYPTOS[best_q4[3]]);
    printf("q5: [%d, %d, %d, %d, %d] ('%c%c%c%c%c')\n",
           best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4],
           KRYPTOS[best_q5[0]], KRYPTOS[best_q5[1]], KRYPTOS[best_q5[2]], KRYPTOS[best_q5[3]], KRYPTOS[best_q5[4]]);
    printf("q6: [%d, %d, %d, %d, %d, %d] ('%c%c%c%c%c%c')\n",
           best_q6[0], best_q6[1], best_q6[2], best_q6[3], best_q6[4], best_q6[5],
           KRYPTOS[best_q6[0]], KRYPTOS[best_q6[1]], KRYPTOS[best_q6[2]],
           KRYPTOS[best_q6[3]], KRYPTOS[best_q6[4]], KRYPTOS[best_q6[5]]);
    printf("q7: [%d, %d, %d, %d, %d, %d, %d] ('%c%c%c%c%c%c%c')\n",
           best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6],
           KRYPTOS[best_q7[0]], KRYPTOS[best_q7[1]], KRYPTOS[best_q7[2]],
           KRYPTOS[best_q7[3]], KRYPTOS[best_q7[4]], KRYPTOS[best_q7[5]], KRYPTOS[best_q7[6]]);
    printf("PT: %s\n", global_best_pt);

    return 0;
}

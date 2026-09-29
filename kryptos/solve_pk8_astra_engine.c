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

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK8_CT[i]];
}

static inline float eval_full(const int *q4, const int *q5, const int *q6, const int *q7, int *out_pt) {
    int pt[N];
    for (int t = 0; t < N; t++) {
        int ks = (q4[t % 4] + q5[t % 5] + q6[t % 6] + q7[t % 7]) % 26;
        int p_kr = (ct_kr[t] - ks + 26) % 26;
        pt[t] = k2std[p_kr];
    }
    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main(int argc, char **argv) {
    int total_restarts = (argc > 1) ? atoi(argv[1]) : 10000;

    load_quads();
    init_tables();

    printf("======================================================================\n");
    printf("Starting Astra-Scale High-Performance Engine on PK8 (%d restarts)\n", total_restarts);
    printf("======================================================================\n");

    float global_best_sc = -999.0f;
    int g_q4[4], g_q5[5], g_q6[6], g_q7[7];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 1999;
        float loc_best_sc = -999.0f;
        int l_q4[4], l_q5[5], l_q6[6], l_q7[7];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 25)
        for (int rep = 0; rep < total_restarts; rep++) {
            int q4[4], q5[5], q6[6], q7[7];
            for (int i = 0; i < 4; i++) q4[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 5; i++) q5[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 6; i++) q6[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;

            float cur_sc = eval_full(q4, q5, q6, q7, NULL);
            float temp = 2.2f;
            float cooling = 0.9994f;

            for (int step = 0; step < 6000; step++) {
                int clk = rand_r(&seed) % 4;
                int pos, old_v, new_v;

                if (clk == 0) {
                    pos = rand_r(&seed) % 4; old_v = q4[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q4[pos] = new_v;
                } else if (clk == 1) {
                    pos = rand_r(&seed) % 5; old_v = q5[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q5[pos] = new_v;
                } else if (clk == 2) {
                    pos = rand_r(&seed) % 6; old_v = q6[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q6[pos] = new_v;
                } else {
                    pos = rand_r(&seed) % 7; old_v = q7[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q7[pos] = new_v;
                }

                float sc = eval_full(q4, q5, q6, q7, NULL);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    if (clk == 0) q4[pos] = old_v;
                    else if (clk == 1) q5[pos] = old_v;
                    else if (clk == 2) q6[pos] = old_v;
                    else q7[pos] = old_v;
                }

                temp *= cooling;
            }

            // Greedy Polish on all 22 positions
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int p = 0; p < 4; p++) {
                    int best_v = q4[p], old_v = q4[p]; float best_d = 0.0f;
                    for (int diff = 1; diff < 26; diff++) {
                        q4[p] = (old_v + diff) % 26;
                        float sc = eval_full(q4, q5, q6, q7, NULL);
                        if (sc - cur_sc > best_d) { best_d = sc - cur_sc; best_v = q4[p]; }
                    }
                    if (best_d > 1e-4f) { q4[p] = best_v; cur_sc += best_d; improved = 1; }
                    else q4[p] = old_v;
                }
                for (int p = 0; p < 5; p++) {
                    int best_v = q5[p], old_v = q5[p]; float best_d = 0.0f;
                    for (int diff = 1; diff < 26; diff++) {
                        q5[p] = (old_v + diff) % 26;
                        float sc = eval_full(q4, q5, q6, q7, NULL);
                        if (sc - cur_sc > best_d) { best_d = sc - cur_sc; best_v = q5[p]; }
                    }
                    if (best_d > 1e-4f) { q5[p] = best_v; cur_sc += best_d; improved = 1; }
                    else q5[p] = old_v;
                }
                for (int p = 0; p < 6; p++) {
                    int best_v = q6[p], old_v = q6[p]; float best_d = 0.0f;
                    for (int diff = 1; diff < 26; diff++) {
                        q6[p] = (old_v + diff) % 26;
                        float sc = eval_full(q4, q5, q6, q7, NULL);
                        if (sc - cur_sc > best_d) { best_d = sc - cur_sc; best_v = q6[p]; }
                    }
                    if (best_d > 1e-4f) { q6[p] = best_v; cur_sc += best_d; improved = 1; }
                    else q6[p] = old_v;
                }
                for (int p = 0; p < 7; p++) {
                    int best_v = q7[p], old_v = q7[p]; float best_d = 0.0f;
                    for (int diff = 1; diff < 26; diff++) {
                        q7[p] = (old_v + diff) % 26;
                        float sc = eval_full(q4, q5, q6, q7, NULL);
                        if (sc - cur_sc > best_d) { best_d = sc - cur_sc; best_v = q7[p]; }
                    }
                    if (best_d > 1e-4f) { q7[p] = best_v; cur_sc += best_d; improved = 1; }
                    else q7[p] = old_v;
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_q4, q4, 4 * sizeof(int));
                memcpy(l_q5, q5, 5 * sizeof(int));
                memcpy(l_q6, q6, 6 * sizeof(int));
                memcpy(l_q7, q7, 7 * sizeof(int));

                int pt_arr[N];
                eval_full(q4, q5, q6, q7, pt_arr);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt_arr[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_q4, l_q4, 4 * sizeof(int));
                memcpy(g_q5, l_q5, 5 * sizeof(int));
                memcpy(g_q6, l_q6, 6 * sizeof(int));
                memcpy(g_q7, l_q7, 7 * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] Global Best: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  PT: %.75s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("%d restarts completed in %.3f s (%.1f restarts/sec)!\n\n",
           total_restarts, elapsed, total_restarts / elapsed);

    printf("======================================================================\n");
    printf("FINAL BEST PK8 RESULT\n");
    printf("======================================================================\n");
    printf("Score: %.4f\n", global_best_sc);
    printf("q4: [%d, %d, %d, %d]\n", g_q4[0], g_q4[1], g_q4[2], g_q4[3]);
    printf("q5: [%d, %d, %d, %d, %d]\n", g_q5[0], g_q5[1], g_q5[2], g_q5[3], g_q5[4]);
    printf("q6: [%d, %d, %d, %d, %d, %d]\n", g_q6[0], g_q6[1], g_q6[2], g_q6[3], g_q6[4], g_q6[5]);
    printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n", g_q7[0], g_q7[1], g_q7[2], g_q7[3], g_q7[4], g_q7[5], g_q7[6]);
    printf("\nFull Plaintext:\n%s\n", g_pt);

    return 0;
}

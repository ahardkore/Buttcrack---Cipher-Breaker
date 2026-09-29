#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 153

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static float quadgrams[26][26][26][26];

void load_quads() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    quadgrams[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    char line[64];
    double total = 5348433.0;
    while (fgets(line, sizeof(line), f)) {
        char g[5]; double cnt;
        if (sscanf(line, "%4s %lf", g, &cnt) == 2) {
            int a = g[0]-'A', b = g[1]-'A', c = g[2]-'A', d = g[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quadgrams[a][b][c][d] = (float)log10(cnt / total);
            }
        }
    }
    fclose(f);
}

static inline float eval_p12(const int *z12, const int *s12, char *pt_out) {
    int pt[N];
    for (int i = 0; i < N; i++) {
        int pt_kr = (z12[i] - s12[i % 12] + 26) % 26;
        char ch = ALPH[pt_kr];
        pt[i] = ch - 'A';
        if (pt_out) pt_out[i] = ch;
    }
    if (pt_out) pt_out[N] = 0;

    float sc = 0;
    for (int i = 0; i < N - 3; i++) {
        sc += quadgrams[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return sc / (N - 3);
}

static inline unsigned int xorshift32(unsigned int *state) {
    unsigned int x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

int main() {
    load_quads();

    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int ct_k[N];
    for (int i=0; i<N; i++) ct_k[i] = k2i[(int)CT[i]];

    // Top q7 candidates:
    // Mask 0: [0, 2, 9, 10, 10, 6, 7]
    // Mask 16: [0, 15, 9, 10, 10, 19, 7]
    // Mask 43: [0, 2, 9, 23, 23, 6, 20]
    int q7_list[4][7] = {
        {0, 2, 9, 23, 23, 6, 20},
        {0, 2, 9, 10, 10, 6, 7},
        {0, 15, 9, 10, 10, 19, 7},
        {0, 15, 9, 10, 10, 6, 7}
    };

    printf("Starting Period-12 Simulated Annealing across top q7 and invariant q5 vectors...\n");
    double t0 = omp_get_wtime();

    float global_best_sc = -1e9f;
    char global_best_pt[N+1];
    int best_q7[7], best_q5[5], best_s12[12];

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 1234567));
        float local_best_sc = -1e9f;
        char local_best_pt[N+1];
        int local_q7[7], local_q5[5], local_best_s12[12];

        #pragma omp for schedule(dynamic, 1)
        for (int q7_idx = 0; q7_idx < 4; q7_idx++) {
            const int *q7 = q7_list[q7_idx];

            // Invariant q5: k5[2] - k5[3] = 7, k5[4] = 1
            for (int k1 = 0; k1 < 26; k1++) {
                for (int k2 = 0; k2 < 26; k2++) {
                    int q5[5];
                    q5[0] = 0;
                    q5[1] = k1;
                    q5[2] = k2;
                    q5[3] = (k2 - 7 + 26) % 26;
                    q5[4] = 1;

                    // Compute z12
                    int z12[N];
                    for (int t=0; t<N; t++) {
                        z12[t] = (ct_k[t] - q5[t % 5] - q7[t % 7] + 52) % 26;
                    }

                    // Simulated annealing on s12
                    int s12[12];
                    for (int c=0; c<12; c++) s12[c] = xorshift32(&seed) % 26;

                    float cur_sc = eval_p12(z12, s12, NULL);
                    float run_best_sc = cur_sc;
                    int run_best_s12[12];
                    memcpy(run_best_s12, s12, sizeof(s12));

                    float temp = 0.8f;
                    int steps = 2500;
                    float cooling = expf(logf(0.001f / 0.8f) / steps);

                    for (int step = 0; step < steps; step++) {
                        int col = xorshift32(&seed) % 12;
                        int old_val = s12[col];
                        s12[col] = (old_val + 1 + (xorshift32(&seed) % 25)) % 26;

                        float new_sc = eval_p12(z12, s12, NULL);
                        float delta = new_sc - cur_sc;

                        if (delta > 0 || ((float)xorshift32(&seed) / 4294967296.0f) < expf(delta / temp)) {
                            cur_sc = new_sc;
                            if (cur_sc > run_best_sc) {
                                run_best_sc = cur_sc;
                                memcpy(run_best_s12, s12, sizeof(s12));
                            }
                        } else {
                            s12[col] = old_val;
                        }
                        temp *= cooling;
                    }

                    if (run_best_sc > local_best_sc) {
                        local_best_sc = run_best_sc;
                        memcpy(local_best_s12, run_best_s12, sizeof(s12));
                        memcpy(local_q7, q7, sizeof(local_q7));
                        memcpy(local_q5, q5, sizeof(q5));
                        eval_p12(z12, local_best_s12, local_best_pt);
                    }

                    if (run_best_sc > -5.8f) {
                        #pragma omp critical
                        {
                            char cand_pt[N+1];
                            eval_p12(z12, run_best_s12, cand_pt);
                            printf("[SURGE] Score: %.4f | q7_idx=%d | q5=[0, %d, %d, %d, 1]\n  PT: %s\n",
                                   run_best_sc, q7_idx, k1, k2, q5[3], cand_pt);
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                memcpy(global_best_pt, local_best_pt, sizeof(global_best_pt));
                memcpy(best_q7, local_q7, sizeof(best_q7));
                memcpy(best_q5, local_q5, sizeof(best_q5));
                memcpy(best_s12, local_best_s12, sizeof(best_s12));
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f seconds! Global best score: %.4f\n", elapsed, global_best_sc);
    printf("q7:  [%d, %d, %d, %d, %d, %d, %d]\n", best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
    printf("q5:  [%d, %d, %d, %d, %d]\n", best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4]);
    printf("s12: [");
    for (int i=0; i<12; i++) printf("%d%s", best_s12[i], i<11?", ":"]\n");
    printf("Plaintext:\n%s\n", global_best_pt);

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const int q2_4[4] = {0, 1, 0, 0};
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
    for (int i = 0; i < 26; i++) alpha_to_std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
}

static inline float eval_full(const int *q4, const int *q7,
                             const int *p1, const int *p2,
                             char *out_plain) {
    // 1. Decrypt CT with (q4, q7) to get X
    char X[N];
    for (int i = 0; i < N; i++) {
        int k = (q4[i % 4] + q7[i % 7]) % 26;
        X[i] = 'A' + alpha_to_std[(c_idx[i] - k + 26) % 26];
    }

    // 2. Invert pi2 to get Y
    char G2[12][12];
    for (int k = 0; k < 12; k++) {
        int col = p2[k];
        for (int r = 0; r < 12; r++) {
            G2[r][col] = X[k * 12 + r];
        }
    }

    char Y[N];
    int idx = 0;
    for (int r = 0; r < 12; r++) {
        for (int c = 0; c < 12; c++) {
            Y[idx++] = G2[r][c];
        }
    }

    // 3. Invert pi1 to get Plain
    char G1[12][12];
    for (int k = 0; k < 12; k++) {
        int col = p1[k];
        for (int r = 0; r < 12; r++) {
            G1[r][col] = Y[k * 12 + r];
        }
    }

    int pt[N];
    idx = 0;
    for (int r = 0; r < 12; r++) {
        for (int c = 0; c < 12; c++) {
            pt[idx++] = G1[r][c] - 'A';
        }
    }

    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    sc /= (N - 3);

    if (out_plain) {
        for (int i = 0; i < N; i++) out_plain[i] = 'A' + pt[i];
        out_plain[N] = '\0';
    }

    return sc;
}

int main(int argc, char **argv) {
    init_tables();
    load_quadgrams();

    // Seeds
    int base_q4[4] = {16, 23, 22, 18};
    int base_q7[7] = {10, 19, 17, 25, 16, 18, 10};
    int base_p1[12] = {0, 6, 10, 3, 11, 2, 1, 5, 4, 8, 7, 9};
    int base_p2[12] = {0, 7, 2, 11, 4, 6, 5, 8, 1, 10, 9, 3};

    char pt[N + 1];
    float init_sc = eval_full(base_q4, base_q7, base_p1, base_p2, pt);
    printf("Initial Score = %.4f\nPT: %s\n", init_sc, pt);

    int restarts = 10000;
    if (argc > 1) restarts = atoi(argv[1]);

    float global_best_sc = init_sc;
    int best_q4[4], best_q7[7], best_p1[12], best_p2[12];
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 9999 + omp_get_thread_num() * 12347;
        float local_best_sc = init_sc;
        int local_best_q4[4], local_best_q7[7], local_best_p1[12], local_best_p2[12];
        char local_best_pt[N + 1] = "";

        #pragma omp for schedule(dynamic, 10)
        for (int r = 0; r < restarts; r++) {
            int cur_q13_4[4], cur_q13_7[7];
            int cur_p1[12], cur_p2[12];

            for (int i = 0; i < 4; i++) cur_q13_4[i] = base_q4[i] % 13;
            for (int i = 0; i < 7; i++) cur_q13_7[i] = base_q7[i] % 13;
            for (int i = 0; i < 12; i++) {
                cur_p1[i] = base_p1[i];
                cur_p2[i] = base_p2[i];
            }

            if (r > 0) {
                // Perturb 1-3 items
                int perts = 1 + rand_r(&seed) % 3;
                for (int p = 0; p < perts; p++) {
                    int type = rand_r(&seed) % 4;
                    if (type == 0) {
                        int idx = 1 + rand_r(&seed) % 3;
                        cur_q13_4[idx] = (cur_q13_4[idx] + 1 + rand_r(&seed) % 12) % 13;
                    } else if (type == 1) {
                        int idx = rand_r(&seed) % 7;
                        cur_q13_7[idx] = (cur_q13_7[idx] + 1 + rand_r(&seed) % 12) % 13;
                    } else if (type == 2) {
                        int i1 = rand_r(&seed) % 12, i2 = rand_r(&seed) % 12;
                        int tmp = cur_p1[i1]; cur_p1[i1] = cur_p1[i2]; cur_p1[i2] = tmp;
                    } else {
                        int i1 = rand_r(&seed) % 12, i2 = rand_r(&seed) % 12;
                        int tmp = cur_p2[i1]; cur_p2[i1] = cur_p2[i2]; cur_p2[i2] = tmp;
                    }
                }
            }

            int cur_q4[4], cur_q7[7];
            for (int i = 0; i < 4; i++) cur_q4[i] = crt(q2_4[i], cur_q13_4[i]);
            for (int i = 0; i < 7; i++) cur_q7[i] = crt(q2_7[i], cur_q13_7[i]);

            float cur_sc = eval_full(cur_q4, cur_q7, cur_p1, cur_p2, NULL);

            // Alternating greedy hill climbing
            int imp = 1;
            int passes = 0;
            while (imp && passes < 15) {
                imp = 0;
                passes++;

                // 1. Optimize Q4
                for (int i = 1; i < 4; i++) {
                    int old_v = cur_q13_4[i];
                    int best_v = old_v;
                    float best_s = cur_sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        cur_q4[i] = crt(q2_4[i], v);
                        float s = eval_full(cur_q4, cur_q7, cur_p1, cur_p2, NULL);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    cur_q13_4[i] = best_v;
                    cur_q4[i] = crt(q2_4[i], best_v);
                    if (best_v != old_v) { cur_sc = best_s; imp = 1; }
                }

                // 2. Optimize Q7
                for (int i = 0; i < 7; i++) {
                    int old_v = cur_q13_7[i];
                    int best_v = old_v;
                    float best_s = cur_sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        cur_q7[i] = crt(q2_7[i], v);
                        float s = eval_full(cur_q4, cur_q7, cur_p1, cur_p2, NULL);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    cur_q13_7[i] = best_v;
                    cur_q7[i] = crt(q2_7[i], best_v);
                    if (best_v != old_v) { cur_sc = best_s; imp = 1; }
                }

                // 3. Optimize p1 swaps
                for (int i = 0; i < 12; i++) {
                    for (int j = i + 1; j < 12; j++) {
                        int tmp = cur_p1[i]; cur_p1[i] = cur_p1[j]; cur_p1[j] = tmp;
                        float s = eval_full(cur_q4, cur_q7, cur_p1, cur_p2, NULL);
                        if (s > cur_sc) {
                            cur_sc = s;
                            imp = 1;
                        } else {
                            tmp = cur_p1[i]; cur_p1[i] = cur_p1[j]; cur_p1[j] = tmp;
                        }
                    }
                }

                // 4. Optimize p2 swaps
                for (int i = 0; i < 12; i++) {
                    for (int j = i + 1; j < 12; j++) {
                        int tmp = cur_p2[i]; cur_p2[i] = cur_p2[j]; cur_p2[j] = tmp;
                        float s = eval_full(cur_q4, cur_q7, cur_p1, cur_p2, NULL);
                        if (s > cur_sc) {
                            cur_sc = s;
                            imp = 1;
                        } else {
                            tmp = cur_p2[i]; cur_p2[i] = cur_p2[j]; cur_p2[j] = tmp;
                        }
                    }
                }
            }

            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                for (int i = 0; i < 4; i++) local_best_q4[i] = cur_q4[i];
                for (int i = 0; i < 7; i++) local_best_q7[i] = cur_q7[i];
                for (int i = 0; i < 12; i++) {
                    local_best_p1[i] = cur_p1[i];
                    local_best_p2[i] = cur_p2[i];
                }
                eval_full(cur_q4, cur_q7, cur_p1, cur_p2, local_best_pt);
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                for (int i = 0; i < 4; i++) best_q4[i] = local_best_q4[i];
                for (int i = 0; i < 7; i++) best_q7[i] = local_best_q7[i];
                for (int i = 0; i < 12; i++) {
                    best_p1[i] = local_best_p1[i];
                    best_p2[i] = local_best_p2[i];
                }
                strcpy(best_pt, local_best_pt);

                printf("\n>>> IMPROVEMENT! Score = %.4f (Base: %.4f)\n", global_best_sc, init_sc);
                printf("  Q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
                printf("  Q7: ["); for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6?"]\n":", ");
                printf("  p1: ["); for (int i = 0; i < 12; i++) printf("%d%s", best_p1[i], i==11?"]\n":", ");
                printf("  p2: ["); for (int i = 0; i < 12; i++) printf("%d%s", best_p2[i], i==11?"]\n":", ");
                printf("  Plaintext: %.120s...\n\n", best_pt);
                fflush(stdout);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f s (%.1f restarts/sec)\n", elapsed, restarts / elapsed);
    printf("Final Best Score = %.4f\n", global_best_sc);
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}

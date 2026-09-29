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
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
    }
}

static inline float eval_score_double(const int *q4, const int *q7,
                                     const int *row_order, const int *col_order,
                                     char *out_plain) {
    int X[N];
    for (int i = 0; i < N; i++) {
        int k = (q4[i % 4] + q7[i % 7]) % 26;
        X[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
    }

    int pt[N];
    int idx = 0;
    for (int r = 0; r < 12; r++) {
        int orig_r = row_order[r];
        for (int c = 0; c < 12; c++) {
            int orig_c = col_order[c];
            pt[idx++] = X[orig_r * 12 + orig_c];
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

    int base_q4[4] = {16, 23, 22, 18};
    int base_q7[7] = {10, 19, 13, 25, 16, 24, 10};
    int base_rows[12] = {9, 4, 1, 5, 6, 3, 11, 2, 10, 0, 8, 7};
    int base_cols[12] = {9, 6, 5, 3, 0, 7, 8, 10, 1, 11, 2, 4};

    char pt[N + 1];
    float init_sc = eval_score_double(base_q4, base_q7, base_rows, base_cols, pt);
    printf("Initial Base Candidate Score = %.4f\nPT: %s\n", init_sc, pt);

    int num_restarts = 100000;
    if (argc > 1) num_restarts = atoi(argv[1]);
    float global_best_sc = init_sc;
    int best_q4[4], best_q7[7], best_rows[12], best_cols[12];
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 777 + omp_get_thread_num() * 88883;
        float local_best_sc = init_sc;
        int local_best_q4[4], local_best_q7[7], local_best_rows[12], local_best_cols[12];
        char local_best_pt[N + 1] = "";

        #pragma omp for schedule(dynamic, 50)
        for (int r = 0; r < num_restarts; r++) {
            int cur_q13_4[4], cur_q13_7[7];
            int cur_rows[12], cur_cols[12];

            for (int i = 0; i < 4; i++) cur_q13_4[i] = base_q4[i] % 13;
            for (int i = 0; i < 7; i++) cur_q13_7[i] = base_q7[i] % 13;
            for (int i = 0; i < 12; i++) {
                cur_rows[i] = base_rows[i];
                cur_cols[i] = base_cols[i];
            }

            // Small perturbation around base: 1 to 3 mutations
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
                    int tmp = cur_rows[i1]; cur_rows[i1] = cur_rows[i2]; cur_rows[i2] = tmp;
                } else {
                    int i1 = rand_r(&seed) % 12, i2 = rand_r(&seed) % 12;
                    int tmp = cur_cols[i1]; cur_cols[i1] = cur_cols[i2]; cur_cols[i2] = tmp;
                }
            }

            int cur_q4[4], cur_q7[7];
            for (int i = 0; i < 4; i++) cur_q4[i] = crt(q2_4[i], cur_q13_4[i]);
            for (int i = 0; i < 7; i++) cur_q7[i] = crt(q2_7[i], cur_q13_7[i]);

            float cur_sc = eval_score_double(cur_q4, cur_q7, cur_rows, cur_cols, NULL);

            // Alternating greedy hill climbing
            int imp = 1;
            int passes = 0;
            while (imp && passes < 15) {
                imp = 0;
                passes++;

                for (int i = 1; i < 4; i++) {
                    int old_v = cur_q13_4[i];
                    int best_v = old_v;
                    float best_s = cur_sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        cur_q4[i] = crt(q2_4[i], v);
                        float s = eval_score_double(cur_q4, cur_q7, cur_rows, cur_cols, NULL);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    cur_q13_4[i] = best_v;
                    cur_q4[i] = crt(q2_4[i], best_v);
                    if (best_v != old_v) { cur_sc = best_s; imp = 1; }
                }

                for (int i = 0; i < 7; i++) {
                    int old_v = cur_q13_7[i];
                    int best_v = old_v;
                    float best_s = cur_sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        cur_q7[i] = crt(q2_7[i], v);
                        float s = eval_score_double(cur_q4, cur_q7, cur_rows, cur_cols, NULL);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    cur_q13_7[i] = best_v;
                    cur_q7[i] = crt(q2_7[i], best_v);
                    if (best_v != old_v) { cur_sc = best_s; imp = 1; }
                }

                for (int c1 = 0; c1 < 12; c1++) {
                    for (int c2 = c1 + 1; c2 < 12; c2++) {
                        int tmp = cur_cols[c1]; cur_cols[c1] = cur_cols[c2]; cur_cols[c2] = tmp;
                        float s = eval_score_double(cur_q4, cur_q7, cur_rows, cur_cols, NULL);
                        if (s > cur_sc) {
                            cur_sc = s;
                            imp = 1;
                        } else {
                            tmp = cur_cols[c1]; cur_cols[c1] = cur_cols[c2]; cur_cols[c2] = tmp;
                        }
                    }
                }

                for (int r1 = 0; r1 < 12; r1++) {
                    for (int r2 = r1 + 1; r2 < 12; r2++) {
                        int tmp = cur_rows[r1]; cur_rows[r1] = cur_rows[r2]; cur_rows[r2] = tmp;
                        float s = eval_score_double(cur_q4, cur_q7, cur_rows, cur_cols, NULL);
                        if (s > cur_sc) {
                            cur_sc = s;
                            imp = 1;
                        } else {
                            tmp = cur_rows[r1]; cur_rows[r1] = cur_rows[r2]; cur_rows[r2] = tmp;
                        }
                    }
                }
            }

            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                for (int i = 0; i < 4; i++) local_best_q4[i] = cur_q4[i];
                for (int i = 0; i < 7; i++) local_best_q7[i] = cur_q7[i];
                for (int i = 0; i < 12; i++) {
                    local_best_rows[i] = cur_rows[i];
                    local_best_cols[i] = cur_cols[i];
                }
                eval_score_double(cur_q4, cur_q7, cur_rows, cur_cols, local_best_pt);
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                for (int i = 0; i < 4; i++) best_q4[i] = local_best_q4[i];
                for (int i = 0; i < 7; i++) best_q7[i] = local_best_q7[i];
                for (int i = 0; i < 12; i++) {
                    best_rows[i] = local_best_rows[i];
                    best_cols[i] = local_best_cols[i];
                }
                strcpy(best_pt, local_best_pt);

                printf("\n>>> IMPROVEMENT! Score = %.4f (Base: %.4f)\n", global_best_sc, init_sc);
                printf("  Q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
                printf("  Q7: ["); for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6?"]\n":", ");
                printf("  Rows: ["); for (int i = 0; i < 12; i++) printf("%d%s", best_rows[i], i==11?"]\n":", ");
                printf("  Cols: ["); for (int i = 0; i < 12; i++) printf("%d%s", best_cols[i], i==11?"]\n":", ");
                printf("  Plaintext: %.120s...\n\n", best_pt);
                fflush(stdout);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted in %.2f s (%.1f restarts/sec)\n", elapsed, num_restarts / elapsed);
    printf("Final Best Score = %.4f\n", global_best_sc);
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}

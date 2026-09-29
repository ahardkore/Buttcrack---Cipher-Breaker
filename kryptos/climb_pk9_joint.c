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

static inline float eval_score(const int *q4, const int *q7, const int *col_order, char *out_plain) {
    // 1. Decrypt ciphertext to stream X
    int X[N];
    for (int i = 0; i < N; i++) {
        int k = (q4[i % 4] + q7[i % 7]) % 26;
        X[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
    }

    // 2. Transposition: 12 columns of 12 rows
    // B[k][r] = X[k * 12 + r]
    // Text: P[r * 12 + c] = B[col_order[c]][r]
    int pt[N];
    int idx = 0;
    for (int r = 0; r < 12; r++) {
        for (int c = 0; c < 12; c++) {
            pt[idx++] = X[col_order[c] * 12 + r];
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

int main() {
    init_tables();
    load_quadgrams();

    printf("Starting Alternating Hill Climbing on PK9 (Q4, Q7, and Column Permutations)...\n");

    // Seeds from Held-Karp best candidate:
    // Q4: [0, 19, 6, 18]
    // Q7: [14, 9, 7, 7, 16, 14, 14]
    // Order: [5, 2, 11, 1, 9, 0, 3, 10, 8, 6, 7, 4]

    int seed_q4[4] = {0, 19, 6, 18};
    int seed_q7[7] = {14, 9, 7, 7, 16, 14, 14};
    int seed_order[12] = {5, 2, 11, 1, 9, 0, 3, 10, 8, 6, 7, 4};

    char pt[N + 1];
    float init_sc = eval_score(seed_q4, seed_q7, seed_order, pt);
    printf("Initial Seed Score = %.4f\nPT: %s\n", init_sc, pt);

    int num_restarts = 5000;
    float global_best_sc = init_sc;
    int best_q4[4], best_q7[7], best_order[12];
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 13579 + omp_get_thread_num() * 24681;
        float local_best_sc = -999.0f;
        int local_best_q4[4], local_best_q7[7], local_best_order[12];
        char local_best_pt[N + 1] = "";

        #pragma omp for schedule(dynamic, 10)
        for (int r = 0; r < num_restarts; r++) {
            int cur_q13_4[4], cur_q13_7[7];
            int cur_order[12];

            if (r == 0) {
                for (int i = 0; i < 4; i++) cur_q13_4[i] = seed_q4[i] % 13;
                for (int i = 0; i < 7; i++) cur_q13_7[i] = seed_q7[i] % 13;
                for (int i = 0; i < 12; i++) cur_order[i] = seed_order[i];
            } else {
                // Perturb near seed or random
                if (rand_r(&seed) % 2 == 0) {
                    for (int i = 0; i < 4; i++) cur_q13_4[i] = seed_q4[i] % 13;
                    for (int i = 0; i < 7; i++) cur_q13_7[i] = seed_q7[i] % 13;
                    for (int i = 0; i < 12; i++) cur_order[i] = seed_order[i];
                    // 1-3 perturbations
                    int perts = 1 + rand_r(&seed) % 3;
                    for (int p = 0; p < perts; p++) {
                        if (rand_r(&seed) % 2 == 0) {
                            int idx = rand_r(&seed) % 7;
                            cur_q13_7[idx] = (cur_q13_7[idx] + 1 + rand_r(&seed) % 12) % 13;
                        } else {
                            int i1 = rand_r(&seed) % 12, i2 = rand_r(&seed) % 12;
                            int tmp = cur_order[i1]; cur_order[i1] = cur_order[i2]; cur_order[i2] = tmp;
                        }
                    }
                } else {
                    for (int i = 0; i < 4; i++) cur_q13_4[i] = rand_r(&seed) % 13;
                    for (int i = 0; i < 7; i++) cur_q13_7[i] = rand_r(&seed) % 13;
                    for (int i = 0; i < 12; i++) cur_order[i] = i;
                    for (int i = 11; i > 0; i--) {
                        int j = rand_r(&seed) % (i + 1);
                        int tmp = cur_order[i]; cur_order[i] = cur_order[j]; cur_order[j] = tmp;
                    }
                }
            }

            int cur_q4[4], cur_q7[7];
            for (int i = 0; i < 4; i++) cur_q4[i] = crt(q2_4[i], cur_q13_4[i]);
            for (int i = 0; i < 7; i++) cur_q7[i] = crt(q2_7[i], cur_q13_7[i]);

            float cur_sc = eval_score(cur_q4, cur_q7, cur_order, NULL);

            // Alternating hill climbing
            int imp = 1;
            int passes = 0;
            while (imp && passes < 15) {
                imp = 0;
                passes++;

                // 1. Optimize Q4 (positions 1..3, pos 0 is gauge)
                for (int i = 1; i < 4; i++) {
                    int old_v = cur_q13_4[i];
                    int best_v = old_v;
                    float best_s = cur_sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        cur_q4[i] = crt(q2_4[i], v);
                        float s = eval_score(cur_q4, cur_q7, cur_order, NULL);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    cur_q13_4[i] = best_v;
                    cur_q4[i] = crt(q2_4[i], best_v);
                    if (best_v != old_v) { cur_sc = best_s; imp = 1; }
                }

                // 2. Optimize Q7 (positions 0..6)
                for (int i = 0; i < 7; i++) {
                    int old_v = cur_q13_7[i];
                    int best_v = old_v;
                    float best_s = cur_sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        cur_q7[i] = crt(q2_7[i], v);
                        float s = eval_score(cur_q4, cur_q7, cur_order, NULL);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    cur_q13_7[i] = best_v;
                    cur_q7[i] = crt(q2_7[i], best_v);
                    if (best_v != old_v) { cur_sc = best_s; imp = 1; }
                }

                // 3. Optimize Column Permutation (all 66 pairwise swaps)
                for (int c1 = 0; c1 < 12; c1++) {
                    for (int c2 = c1 + 1; c2 < 12; c2++) {
                        int tmp = cur_order[c1]; cur_order[c1] = cur_order[c2]; cur_order[c2] = tmp;
                        float s = eval_score(cur_q4, cur_q7, cur_order, NULL);
                        if (s > cur_sc) {
                            cur_sc = s;
                            imp = 1;
                        } else {
                            // Revert
                            tmp = cur_order[c1]; cur_order[c1] = cur_order[c2]; cur_order[c2] = tmp;
                        }
                    }
                }
            }

            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                for (int i = 0; i < 4; i++) local_best_q4[i] = cur_q4[i];
                for (int i = 0; i < 7; i++) local_best_q7[i] = cur_q7[i];
                for (int i = 0; i < 12; i++) local_best_order[i] = cur_order[i];
                eval_score(cur_q4, cur_q7, cur_order, local_best_pt);
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                for (int i = 0; i < 4; i++) best_q4[i] = local_best_q4[i];
                for (int i = 0; i < 7; i++) best_q7[i] = local_best_q7[i];
                for (int i = 0; i < 12; i++) best_order[i] = local_best_order[i];
                strcpy(best_pt, local_best_pt);

                printf("\n>>> CANDIDATE HIT! Score = %.4f (Base: %.4f)\n", global_best_sc, init_sc);
                printf("  Q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
                printf("  Q7: ["); for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6?"]\n":", ");
                printf("  Order: ["); for (int i = 0; i < 12; i++) printf("%d%s", best_order[i], i==11?"]\n":", ");
                printf("  Plaintext: %.120s...\n\n", best_pt);
                fflush(stdout);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted in %.2f s (%.1f restarts/sec)\n", elapsed, num_restarts / elapsed);
    printf("Final Best Score = %.4f\n", global_best_sc);
    printf("Q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
    printf("Q7: ["); for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6?"]\n":", ");
    printf("Order: ["); for (int i = 0; i < 12; i++) printf("%d%s", best_order[i], i==11?"]\n":", ");
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}

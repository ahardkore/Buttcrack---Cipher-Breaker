#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const int q4[4] = {16, 23, 22, 18};
static const int q7[7] = {10, 19, 17, 25, 16, 18, 10};

static int c_idx[N];
static int alpha_to_std[26];
static char X[N + 1];
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

    for (int i = 0; i < N; i++) {
        int k = (q4[i % 4] + q7[i % 7]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        X[i] = 'A' + alpha_to_std[p];
    }
    X[N] = '\0';
}

static inline float eval_perm(const int *col_order, char *out_plain) {
    int pt[N];
    int idx = 0;
    for (int r = 0; r < 12; r++) {
        for (int c = 0; c < 12; c++) {
            pt[idx++] = X[r * 12 + col_order[c]] - 'A';
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

    int restarts = 1000;
    if (argc > 1) restarts = atoi(argv[1]);

    printf("Starting Ultra-Fast SA on PK9 12-Column Permutations (%d restarts)...\n", restarts);

    // Initial seed: [8, 0, 7, 1, 10, 11, 2, 3, 6, 5, 9, 4]
    int seed_order[12] = {8, 0, 7, 1, 10, 11, 2, 3, 6, 5, 9, 4};
    char init_pt[N + 1];
    float init_sc = eval_perm(seed_order, init_pt);
    printf("Initial Seed Quadgram Score = %.4f\n", init_sc);

    float global_best_sc = init_sc;
    int best_order[12];
    char best_pt[N + 1] = "";
    for (int i = 0; i < 12; i++) best_order[i] = seed_order[i];
    strcpy(best_pt, init_pt);

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 777;
        float local_best_sc = init_sc;
        int local_best_order[12];
        char local_best_pt[N + 1] = "";
        for (int i = 0; i < 12; i++) local_best_order[i] = seed_order[i];

        #pragma omp for schedule(dynamic, 10)
        for (int r = 0; r < restarts; r++) {
            int cur_order[12];
            if (r == 0) {
                for (int i = 0; i < 12; i++) cur_order[i] = seed_order[i];
            } else if (r < restarts / 2) {
                // Perturb near seed
                for (int i = 0; i < 12; i++) cur_order[i] = seed_order[i];
                int perts = 1 + rand_r(&seed) % 3;
                for (int p = 0; p < perts; p++) {
                    int i1 = rand_r(&seed) % 12, i2 = rand_r(&seed) % 12;
                    int tmp = cur_order[i1]; cur_order[i1] = cur_order[i2]; cur_order[i2] = tmp;
                }
            } else {
                // Pure random
                for (int i = 0; i < 12; i++) cur_order[i] = i;
                for (int i = 11; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int tmp = cur_order[i]; cur_order[i] = cur_order[j]; cur_order[j] = tmp;
                }
            }

            float cur_sc = eval_perm(cur_order, NULL);

            float T = 2.0f;
            float T_end = 0.001f;
            int steps = 20000;
            float decay = powf(T_end / T, 1.0f / steps);

            for (int step = 0; step < steps; step++) {
                int i1 = rand_r(&seed) % 12;
                int i2 = rand_r(&seed) % 12;
                while (i2 == i1) i2 = rand_r(&seed) % 12;

                // Swap
                int tmp = cur_order[i1]; cur_order[i1] = cur_order[i2]; cur_order[i2] = tmp;
                float new_sc = eval_perm(cur_order, NULL);
                float delta = new_sc - cur_sc;

                if (delta > 0 || (rand_r(&seed) / (float)RAND_MAX) < expf(delta / T)) {
                    cur_sc = new_sc;
                } else {
                    // Revert
                    tmp = cur_order[i1]; cur_order[i1] = cur_order[i2]; cur_order[i2] = tmp;
                }
                T *= decay;
            }

            // Quench
            int imp = 1;
            while (imp) {
                imp = 0;
                for (int i = 0; i < 12; i++) {
                    for (int j = i + 1; j < 12; j++) {
                        int tmp = cur_order[i]; cur_order[i] = cur_order[j]; cur_order[j] = tmp;
                        float s = eval_perm(cur_order, NULL);
                        if (s > cur_sc) {
                            cur_sc = s;
                            imp = 1;
                        } else {
                            tmp = cur_order[i]; cur_order[i] = cur_order[j]; cur_order[j] = tmp;
                        }
                    }
                }
            }

            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                for (int i = 0; i < 12; i++) local_best_order[i] = cur_order[i];
                eval_perm(cur_order, local_best_pt);

                if (local_best_sc > -6.0f) {
                    #pragma omp critical
                    {
                        if (local_best_sc > global_best_sc) {
                            global_best_sc = local_best_sc;
                            for (int i = 0; i < 12; i++) best_order[i] = local_best_order[i];
                            strcpy(best_pt, local_best_pt);

                            printf("\n>>> CANDIDATE HIT! Score = %.4f\n", global_best_sc);
                            printf("  Order: [");
                            for (int i = 0; i < 12; i++) printf("%d%s", best_order[i], i==11?"]\n":", ");
                            printf("  Plaintext: %.120s...\n\n", best_pt);
                            fflush(stdout);
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                for (int i = 0; i < 12; i++) best_order[i] = local_best_order[i];
                strcpy(best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted %d restarts in %.2f s (%.1f restarts/sec)\n",
           restarts, elapsed, restarts / elapsed);
    printf("Global Best Quadgram Score = %.4f\n", global_best_sc);
    printf("Optimal Column Order: [");
    for (int i = 0; i < 12; i++) printf("%d%s", best_order[i], i==11?"]\n":", ");
    printf("\nDecrypted Plaintext (Row by Row):\n");
    for (int r = 0; r < 12; r++) {
        printf("Row %2d: %.12s\n", r, best_pt + r * 12);
    }
    printf("\nFull Plaintext:\n%s\n", best_pt);

    FILE *fout = fopen("pk9_solution_pt.txt", "w");
    fprintf(fout, "Score: %.4f\nOrder: [", global_best_sc);
    for (int i = 0; i < 12; i++) fprintf(fout, "%d%s", best_order[i], i==11?"]\n":", ");
    fprintf(fout, "%s\n", best_pt);
    fclose(fout);

    return 0;
}

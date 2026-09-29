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

// Invert double columnar transposition:
// Plaintext P -> ColTrans(pi1) -> Y -> ColTrans(pi2) -> X
// Inverting:
// X is read into 12 columns of 12 rows: X_col[c][r] = X[c * 12 + r] (or X[r * 12 + c])
// Under PK2/PK6 standard convention:
// Transposition reads down columns in key order:
// Text is written into rows: Grid[r][c] = Plain[r * W + c]
// Ciphertext is read down columns: Col[order[k]]
// So Ciphertext[k * H + r] = Grid[r][order[k]]
// Inverting: Grid[r][order[k]] = Ciphertext[k * H + r]
// Then Plain[r * W + c] = Grid[r][c].
static inline float eval_double_col(const int *p1, const int *p2, char *out_plain) {
    // Stage 1: Invert pi2 on X to get Y
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

    // Stage 2: Invert pi1 on Y to get Plain
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

    int restarts = 2000;
    if (argc > 1) restarts = atoi(argv[1]);

    printf("Starting Double Columnar SA on PK9 (%d restarts, 100,000 steps each)...\n", restarts);

    float global_best_sc = -999.0f;
    int best_p1[12], best_p2[12];
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 4321 + omp_get_thread_num() * 11119;
        float local_best_sc = -999.0f;
        int local_best_p1[12], local_best_p2[12];
        char local_best_pt[N + 1] = "";

        #pragma omp for schedule(dynamic, 1)
        for (int r = 0; r < restarts; r++) {
            int cur_p1[12], cur_p2[12];
            for (int i = 0; i < 12; i++) { cur_p1[i] = i; cur_p2[i] = i; }

            // Random shuffle
            for (int i = 11; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = cur_p1[i]; cur_p1[i] = cur_p1[j]; cur_p1[j] = tmp;
            }
            for (int i = 11; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = cur_p2[i]; cur_p2[i] = cur_p2[j]; cur_p2[j] = tmp;
            }

            float cur_sc = eval_double_col(cur_p1, cur_p2, NULL);

            float T = 3.0f;
            float T_end = 0.002f;
            int steps = 100000;
            float decay = powf(T_end / T, 1.0f / steps);

            for (int step = 0; step < steps; step++) {
                int which = rand_r(&seed) % 2;
                int i1 = rand_r(&seed) % 12;
                int i2 = rand_r(&seed) % 12;
                while (i2 == i1) i2 = rand_r(&seed) % 12;

                if (which == 0) {
                    int tmp = cur_p1[i1]; cur_p1[i1] = cur_p1[i2]; cur_p1[i2] = tmp;
                } else {
                    int tmp = cur_p2[i1]; cur_p2[i1] = cur_p2[i2]; cur_p2[i2] = tmp;
                }

                float new_sc = eval_double_col(cur_p1, cur_p2, NULL);
                float delta = new_sc - cur_sc;

                if (delta > 0 || (rand_r(&seed) / (float)RAND_MAX) < expf(delta / T)) {
                    cur_sc = new_sc;
                } else {
                    // Revert
                    if (which == 0) {
                        int tmp = cur_p1[i1]; cur_p1[i1] = cur_p1[i2]; cur_p1[i2] = tmp;
                    } else {
                        int tmp = cur_p2[i1]; cur_p2[i1] = cur_p2[i2]; cur_p2[i2] = tmp;
                    }
                }
                T *= decay;
            }

            // Quench
            int imp = 1;
            while (imp) {
                imp = 0;
                for (int which = 0; which < 2; which++) {
                    int *p = (which == 0) ? cur_p1 : cur_p2;
                    for (int i = 0; i < 12; i++) {
                        for (int j = i + 1; j < 12; j++) {
                            int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                            float s = eval_double_col(cur_p1, cur_p2, NULL);
                            if (s > cur_sc) {
                                cur_sc = s;
                                imp = 1;
                            } else {
                                tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                            }
                        }
                    }
                }
            }

            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                for (int i = 0; i < 12; i++) {
                    local_best_p1[i] = cur_p1[i];
                    local_best_p2[i] = cur_p2[i];
                }
                eval_double_col(cur_p1, cur_p2, local_best_pt);

                if (local_best_sc > -6.35f) {
                    #pragma omp critical
                    {
                        if (local_best_sc > global_best_sc) {
                            global_best_sc = local_best_sc;
                            for (int i = 0; i < 12; i++) {
                                best_p1[i] = local_best_p1[i];
                                best_p2[i] = local_best_p2[i];
                            }
                            strcpy(best_pt, local_best_pt);

                            printf("\n>>> CANDIDATE HIT! Score = %.4f (Native English: -4.3 to -4.5)\n", global_best_sc);
                            printf("  p1: ["); for (int i = 0; i < 12; i++) printf("%d%s", best_p1[i], i==11?"]\n":", ");
                            printf("  p2: ["); for (int i = 0; i < 12; i++) printf("%d%s", best_p2[i], i==11?"]\n":", ");
                            printf("  Plaintext: %s\n\n", best_pt);
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
                for (int i = 0; i < 12; i++) {
                    best_p1[i] = local_best_p1[i];
                    best_p2[i] = local_best_p2[i];
                }
                strcpy(best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished %d restarts in %.2f s (%.1f restarts/sec)\n",
           restarts, elapsed, restarts / elapsed);
    printf("Global Best Quadgram Score = %.4f\n", global_best_sc);
    printf("p1: ["); for (int i = 0; i < 12; i++) printf("%d%s", best_p1[i], i==11?"]\n":", ");
    printf("p2: ["); for (int i = 0; i < 12; i++) printf("%d%s", best_p2[i], i==11?"]\n":", ");
    printf("Decrypted Plaintext:\n%s\n", best_pt);

    return 0;
}

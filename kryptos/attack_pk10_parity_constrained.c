#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define W 42
#define H 12

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
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int c_idx[N];
static int k2std[26];

// Proven GF(2) parity vectors
static const int par_q7[7] = {0, 1, 1, 1, 0, 0, 0};
static const int par_q8[8] = {0, 0, 0, 1, 0, 1, 0, 0};
static const int par_q9[9] = {0, 0, 1, 1, 1, 1, 0, 0, 0};

void init_tables() {
    for (int i = 0; i < 26; i++) k2std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
}

static inline float score_matrix(const int *pt) {
    float sc = 0.0f;
    for (int r = 0; r < H; r++) {
        const int *row = pt + r * W;
        for (int c = 0; c < W - 3; c++) {
            sc += quad[row[c]][row[c+1]][row[c+2]][row[c+3]];
        }
    }
    return sc / (H * (W - 3));
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 1000;

    printf("======================================================================\n");
    printf("PK10 Attack: Parity-Constrained 3-Clock + W=42 TSP Optimization\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    float global_best_sc = -999.0f;
    int best_q7[7], best_q8[8], best_q9[9], best_order[W];
    char best_pt[N + 1];

    const int init_order[W] = {
        30, 38, 21, 3, 25, 40, 17, 36, 12, 10, 29, 33, 8, 41, 7, 32, 20, 0, 23, 34, 19,
        2, 22, 27, 6, 37, 31, 24, 39, 18, 28, 35, 11, 13, 4, 26, 15, 5, 1, 14, 16, 9
    };

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 13579 + omp_get_thread_num() * 4444;
        float loc_best = -999.0f;
        int loc_q7[7], loc_q8[8], loc_q9[9], loc_order[W];
        char loc_pt[N + 1];

        #pragma omp for schedule(dynamic, 5)
        for (int rep = 0; rep < restarts; rep++) {
            int q7[7], q8[8], q9[9], order[W];

            // Parity-constrained clock initialization:
            // v = par + 2 * (rand % 13)
            q7[0] = 0;
            for (int i = 1; i < 7; i++) q7[i] = par_q7[i] + 2 * (rand_r(&seed) % 13);
            q8[0] = 0;
            for (int i = 1; i < 8; i++) q8[i] = par_q8[i] + 2 * (rand_r(&seed) % 13);
            for (int i = 0; i < 9; i++) q9[i] = par_q9[i] + 2 * (rand_r(&seed) % 13);

            memcpy(order, init_order, W * sizeof(int));
            if (rand_r(&seed) % 2 == 0) {
                // perturb order
                int a = rand_r(&seed) % W, b = rand_r(&seed) % W;
                int t = order[a]; order[a] = order[b]; order[b] = t;
            }

            int Z[N], grid[H][W], pt[N];
            for (int i = 0; i < N; i++) {
                int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                int p = (c_idx[i] - k + 26) % 26;
                Z[i] = k2std[p];
            }

            // Fill grid column by column
            int idx = 0;
            for (int c = 0; c < W; c++) {
                int col = order[c];
                for (int r = 0; r < H; r++) grid[r][col] = Z[idx++];
            }
            idx = 0;
            for (int r = 0; r < H; r++) {
                for (int c = 0; c < W; c++) pt[idx++] = grid[r][c];
            }
            float cur_sc = score_matrix(pt);

            // Annealing
            float temp = 0.5f;
            float cooling = 0.995f;

            for (int step = 0; step < 2000; step++) {
                int move = rand_r(&seed) % 30;

                if (move < 6) {
                    // change q7
                    int pos = 1 + move;
                    int old_v = q7[pos];
                    q7[pos] = par_q7[pos] + 2 * (rand_r(&seed) % 13);

                    for (int i = pos; i < N; i += 7) {
                        int k = (q7[pos] + q8[i % 8] + q9[i % 9]) % 26;
                        int p = (c_idx[i] - k + 26) % 26;
                        Z[i] = k2std[p];
                    }
                    idx = 0;
                    for (int c = 0; c < W; c++) {
                        int col = order[c];
                        for (int r = 0; r < H; r++) grid[r][col] = Z[idx++];
                    }
                    idx = 0;
                    for (int r = 0; r < H; r++)
                        for (int c = 0; c < W; c++) pt[idx++] = grid[r][c];

                    float sc = score_matrix(pt);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        q7[pos] = old_v;
                        for (int i = pos; i < N; i += 7) {
                            int k = (old_v + q8[i % 8] + q9[i % 9]) % 26;
                            int p = (c_idx[i] - k + 26) % 26;
                            Z[i] = k2std[p];
                        }
                    }
                } else if (move < 13) {
                    // change q8
                    int pos = move - 6;
                    if (pos == 0) pos = 1; // gauge
                    int old_v = q8[pos];
                    q8[pos] = par_q8[pos] + 2 * (rand_r(&seed) % 13);

                    for (int i = pos; i < N; i += 8) {
                        int k = (q7[i % 7] + q8[pos] + q9[i % 9]) % 26;
                        int p = (c_idx[i] - k + 26) % 26;
                        Z[i] = k2std[p];
                    }
                    idx = 0;
                    for (int c = 0; c < W; c++) {
                        int col = order[c];
                        for (int r = 0; r < H; r++) grid[r][col] = Z[idx++];
                    }
                    idx = 0;
                    for (int r = 0; r < H; r++)
                        for (int c = 0; c < W; c++) pt[idx++] = grid[r][c];

                    float sc = score_matrix(pt);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        q8[pos] = old_v;
                        for (int i = pos; i < N; i += 8) {
                            int k = (q7[i % 7] + old_v + q9[i % 9]) % 26;
                            int p = (c_idx[i] - k + 26) % 26;
                            Z[i] = k2std[p];
                        }
                    }
                } else if (move < 22) {
                    // change q9
                    int pos = move - 13;
                    int old_v = q9[pos];
                    q9[pos] = par_q9[pos] + 2 * (rand_r(&seed) % 13);

                    for (int i = pos; i < N; i += 9) {
                        int k = (q7[i % 7] + q8[i % 8] + q9[pos]) % 26;
                        int p = (c_idx[i] - k + 26) % 26;
                        Z[i] = k2std[p];
                    }
                    idx = 0;
                    for (int c = 0; c < W; c++) {
                        int col = order[c];
                        for (int r = 0; r < H; r++) grid[r][col] = Z[idx++];
                    }
                    idx = 0;
                    for (int r = 0; r < H; r++)
                        for (int c = 0; c < W; c++) pt[idx++] = grid[r][c];

                    float sc = score_matrix(pt);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        q9[pos] = old_v;
                        for (int i = pos; i < N; i += 9) {
                            int k = (q7[i % 7] + q8[i % 8] + old_v) % 26;
                            int p = (c_idx[i] - k + 26) % 26;
                            Z[i] = k2std[p];
                        }
                    }
                } else {
                    // swap in order
                    int a = rand_r(&seed) % W;
                    int b = rand_r(&seed) % W;
                    if (a != b) {
                        int t = order[a]; order[a] = order[b]; order[b] = t;
                        idx = 0;
                        for (int c = 0; c < W; c++) {
                            int col = order[c];
                            for (int r = 0; r < H; r++) grid[r][col] = Z[idx++];
                        }
                        idx = 0;
                        for (int r = 0; r < H; r++)
                            for (int c = 0; c < W; c++) pt[idx++] = grid[r][c];

                        float sc = score_matrix(pt);
                        float delta = sc - cur_sc;
                        if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                            cur_sc = sc;
                        } else {
                            order[b] = order[a]; order[a] = t;
                        }
                    }
                }

                temp *= cooling;
            }

            if (cur_sc > loc_best) {
                loc_best = cur_sc;
                memcpy(loc_q7, q7, 7 * sizeof(int));
                memcpy(loc_q8, q8, 8 * sizeof(int));
                memcpy(loc_q9, q9, 9 * sizeof(int));
                memcpy(loc_order, order, W * sizeof(int));
                for (int i = 0; i < N; i++) loc_pt[i] = 'A' + pt[i];
                loc_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best > global_best_sc) {
                global_best_sc = loc_best;
                memcpy(best_q7, loc_q7, 7 * sizeof(int));
                memcpy(best_q8, loc_q8, 8 * sizeof(int));
                memcpy(best_q9, loc_q9, 9 * sizeof(int));
                memcpy(best_order, loc_order, W * sizeof(int));
                strcpy(best_pt, loc_pt);
                printf("[Thread %d] Record: Score=%.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  Q7: [");
                for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6?"":", ");
                printf("]\n  Q8: [");
                for (int i = 0; i < 8; i++) printf("%d%s", best_q8[i], i==7?"":", ");
                printf("]\n  Q9: [");
                for (int i = 0; i < 9; i++) printf("%d%s", best_q9[i], i==8?"":", ");
                printf("]\n  PT: %.60s...\n\n", best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("PK10 ATTACK COMPLETED in %.2f s | Best Score: %.4f\n", elapsed, global_best_sc);
    printf("======================================================================\n");
    printf("Final Q7: [");
    for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6?"":", ");
    printf("]\nFinal Q8: [");
    for (int i = 0; i < 8; i++) printf("%d%s", best_q8[i], i==7?"":", ");
    printf("]\nFinal Q9: [");
    for (int i = 0; i < 9; i++) printf("%d%s", best_q9[i], i==8?"":", ");
    printf("]\n\nFull Plaintext:\n%s\n\n", best_pt);

    printf("Plaintext layout in 12 rows of 42 chars:\n");
    for (int r = 0; r < H; r++) {
        char buf[W + 1];
        memcpy(buf, best_pt + r * W, W);
        buf[W] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}

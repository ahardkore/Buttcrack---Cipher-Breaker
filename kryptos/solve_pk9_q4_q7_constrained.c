#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W1 18
#define H1 8
#define W2 8
#define H2 18

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
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int c_idx[N];
static int alpha_to_std[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
    }
}

static inline void compute_z(const int *q4, const int *q7, int *Z) {
    for (int i = 0; i < N; i++) {
        int k = (q4[i % 4] + q7[i % 7]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        Z[i] = alpha_to_std[p];
    }
}

// Invert double columnar:
// intermediate Z is obtained from plaintext P via:
// P (8x18) -> permute columns by p1 -> read out columns -> write into (18x8) -> permute columns by p2 -> read out columns -> Z
// To invert:
// from Z, write by columns into (18x8) using inverse p2 -> read by rows -> write by columns into (8x18) using inverse p1 -> read by rows = P
static inline float eval_trans(const int *Z, const int *inv_p1, const int *inv_p2, int *pt_out) {
    int g2[H2][W2];
    int idx = 0;
    for (int c = 0; c < W2; c++) {
        int orig_col = inv_p2[c];
        for (int r = 0; r < H2; r++) {
            g2[r][orig_col] = Z[idx++];
        }
    }
    int mid[N];
    idx = 0;
    for (int r = 0; r < H2; r++) {
        for (int c = 0; c < W2; c++) {
            mid[idx++] = g2[r][c];
        }
    }

    int g1[H1][W1];
    idx = 0;
    for (int c = 0; c < W1; c++) {
        int orig_col = inv_p1[c];
        for (int r = 0; r < H1; r++) {
            g1[r][orig_col] = mid[idx++];
        }
    }
    idx = 0;
    for (int r = 0; r < H1; r++) {
        for (int c = 0; c < W1; c++) {
            pt_out[idx++] = g1[r][c];
        }
    }

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt_out[i]][pt_out[i+1]][pt_out[i+2]][pt_out[i+3]];
    }
    return s / (N - 3);
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 20000;

    printf("======================================================================\n");
    printf("PK9 Constrained Q4 (x4) + Q7 (x7) Sum-Clock + Double Columnar (18x8)\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    // Baseline permutations from (18, 8) breakthrough
    int base_p1[W1] = {5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6};
    int base_p2[W2] = {4, 0, 6, 5, 3, 2, 7, 1};

    int inv_p1[W1], inv_p2[W2];
    for (int i = 0; i < W1; i++) inv_p1[base_p1[i]] = i;
    for (int i = 0; i < W2; i++) inv_p2[base_p2[i]] = i;

    float global_best_sc = -999.0f;
    int g_q4[4], g_q7[7];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 7789;
        float loc_best_sc = -999.0f;
        int l_q4[4], l_q7[7];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 100)
        for (int rep = 0; rep < restarts; rep++) {
            int q4[4], q7[7];
            q4[0] = 0;
            for (int i = 1; i < 4; i++) q4[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;

            int Z[N], pt[N];
            compute_z(q4, q7, Z);
            float cur_sc = eval_trans(Z, inv_p1, inv_p2, pt);

            // Coordinate descent / simulated annealing over (q4, q7)
            float temp = 1.0f;
            float cooling = 0.995f;

            for (int step = 0; step < 1500; step++) {
                int move = rand_r(&seed) % 10;
                int old_v, new_v;
                if (move < 3) {
                    int pos = 1 + move; // 1, 2, 3
                    old_v = q4[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q4[pos] = new_v;
                    compute_z(q4, q7, Z);
                    float sc = eval_trans(Z, inv_p1, inv_p2, pt);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        q4[pos] = old_v;
                        compute_z(q4, q7, Z);
                    }
                } else {
                    int pos = move - 3; // 0..6
                    old_v = q7[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q7[pos] = new_v;
                    compute_z(q4, q7, Z);
                    float sc = eval_trans(Z, inv_p1, inv_p2, pt);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        q7[pos] = old_v;
                        compute_z(q4, q7, Z);
                    }
                }
                temp *= cooling;
            }

            // Polish with greedy coordinate descent
            int imp = 1;
            while (imp) {
                imp = 0;
                for (int pos = 1; pos < 4; pos++) {
                    int orig = q4[pos];
                    for (int cand = 0; cand < 26; cand++) {
                        if (cand == orig) continue;
                        q4[pos] = cand;
                        compute_z(q4, q7, Z);
                        float sc = eval_trans(Z, inv_p1, inv_p2, pt);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            orig = cand;
                            imp = 1;
                        }
                    }
                    q4[pos] = orig;
                }
                for (int pos = 0; pos < 7; pos++) {
                    int orig = q7[pos];
                    for (int cand = 0; cand < 26; cand++) {
                        if (cand == orig) continue;
                        q7[pos] = cand;
                        compute_z(q4, q7, Z);
                        float sc = eval_trans(Z, inv_p1, inv_p2, pt);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            orig = cand;
                            imp = 1;
                        }
                    }
                    q7[pos] = orig;
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_q4, q4, 4 * sizeof(int));
                memcpy(l_q7, q7, 7 * sizeof(int));
                compute_z(q4, q7, Z);
                eval_trans(Z, inv_p1, inv_p2, pt);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_q4, l_q4, 4 * sizeof(int));
                memcpy(g_q7, l_q7, 7 * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] NEW RECORD: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  Q4: [%d, %d, %d, %d]\n", g_q4[0], g_q4[1], g_q4[2], g_q4[3]);
                printf("  Q7: [%d, %d, %d, %d, %d, %d, %d]\n", g_q7[0], g_q7[1], g_q7[2], g_q7[3], g_q7[4], g_q7[5], g_q7[6]);
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("OPTIMIZATION COMPLETED (%d restarts in %.3f s)\n", restarts, elapsed);
    printf("======================================================================\n");
    printf("Global Best Score: %.4f\n", global_best_sc);
    printf("Q4: [%d, %d, %d, %d] (KR: %c%c%c%c)\n",
           g_q4[0], g_q4[1], g_q4[2], g_q4[3],
           KRYPTOS[g_q4[0]], KRYPTOS[g_q4[1]], KRYPTOS[g_q4[2]], KRYPTOS[g_q4[3]]);
    printf("Q7: [%d, %d, %d, %d, %d, %d, %d] (KR: %c%c%c%c%c%c%c)\n",
           g_q7[0], g_q7[1], g_q7[2], g_q7[3], g_q7[4], g_q7[5], g_q7[6],
           KRYPTOS[g_q7[0]], KRYPTOS[g_q7[1]], KRYPTOS[g_q7[2]], KRYPTOS[g_q7[3]],
           KRYPTOS[g_q7[4]], KRYPTOS[g_q7[5]], KRYPTOS[g_q7[6]]);

    printf("\nFull Plaintext:\n%s\n\n", g_pt);
    printf("Plaintext layout in 8 rows of 18 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[W1 + 1];
        memcpy(buf, g_pt + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}

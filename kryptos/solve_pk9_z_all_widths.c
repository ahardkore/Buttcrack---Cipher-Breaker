#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144

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
static int Z[N];

void init_z() {
    for (int i = 0; i < 26; i++) alpha_to_std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;

    const int s[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};
    for (int i = 0; i < N; i++) {
        int k = s[i % 28];
        int p = (c_idx[i] - k + 26) % 26;
        Z[i] = alpha_to_std[p];
    }
}

// Invert single columnar transposition:
// Z was produced by writing plaintext P (H x W) by rows, reading out columns permuted by perm.
// To invert: write Z into columns according to perm, read out by rows = P.
static inline float eval_single_col(int W, const int *perm, int *pt_out) {
    int H = N / W;
    int grid[H][W];
    int idx = 0;
    for (int c = 0; c < W; c++) {
        int col_idx = perm[c];
        for (int r = 0; r < H; r++) {
            grid[r][col_idx] = Z[idx++];
        }
    }
    idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            pt_out[idx++] = grid[r][c];
        }
    }
    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        sc += quad[pt_out[i]][pt_out[i+1]][pt_out[i+2]][pt_out[i+3]];
    }
    return sc / (N - 3);
}

void test_width(int W, int restarts) {
    int H = N / W;
    float global_best_sc = -999.0f;
    int g_perm[W];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 1234 + W * 101 + omp_get_thread_num() * 777;
        float loc_best_sc = -999.0f;
        int l_perm[W];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 50)
        for (int rep = 0; rep < restarts; rep++) {
            int perm[W];
            for (int i = 0; i < W; i++) perm[i] = i;
            for (int i = W - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
            }

            int pt[N];
            float cur_sc = eval_single_col(W, perm, pt);
            float temp = 1.0f;
            float cooling = 0.995f;

            for (int step = 0; step < 1200; step++) {
                int c1 = rand_r(&seed) % W;
                int c2 = rand_r(&seed) % W;
                if (c1 == c2) continue;
                int tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;

                float sc = eval_single_col(W, perm, pt);
                float delta = sc - cur_sc;
                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    perm[c2] = perm[c1]; perm[c1] = tmp;
                }
                temp *= cooling;
            }

            // Polish 2-opt
            int imp = 1;
            while (imp) {
                imp = 0;
                for (int i = 0; i < W - 1; i++) {
                    for (int j = i + 1; j < W; j++) {
                        int t = perm[i]; perm[i] = perm[j]; perm[j] = t;
                        float sc = eval_single_col(W, perm, pt);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            imp = 1;
                        } else {
                            perm[j] = perm[i]; perm[i] = t;
                        }
                    }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_perm, perm, W * sizeof(int));
                eval_single_col(W, perm, pt);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_perm, l_perm, W * sizeof(int));
                strcpy(g_pt, l_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Width %2d (Height %2d): Best Score = %8.4f (Time: %.3fs)\n", W, H, global_best_sc, elapsed);
    printf("  Order: [");
    for (int i = 0; i < W; i++) printf("%d%s", g_perm[i], i==W-1?"":", ");
    printf("]\n");
    printf("  PT: %.65s...\n\n", g_pt);
}

int main(int argc, char **argv) {
    load_quads();
    init_z();

    printf("======================================================================\n");
    printf("Exhaustive Single-Columnar Transposition Sweep on PK9 Intermediate Z\n");
    printf("Testing factor widths: 6, 8, 9, 12, 16, 18, 24\n");
    printf("======================================================================\n\n");

    int widths[] = {6, 8, 9, 12, 16, 18, 24};
    int n_widths = sizeof(widths) / sizeof(widths[0]);

    for (int i = 0; i < n_widths; i++) {
        test_width(widths[i], 3000);
    }

    return 0;
}

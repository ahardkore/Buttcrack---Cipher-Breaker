#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define W 12
#define H 12
#define N 144

// The 12 rows of G (transposed Z)
static const char *G_rows[12] = {
    "UIRERTAHIHIO",
    "TSMRLOCNSDHH",
    "NWOWEMOSALSO",
    "MDTUNRNAUENO",
    "SOIHFSNLIRSN",
    "ASSETIRNFNSW",
    "OCEHMAHADCAE",
    "FTGTDNIONOCE",
    "WFETREEEEPSD",
    "SALRNEEIFDIH",
    "UITAONLOFSSI",
    "EHAHSSDSOOFU"
};

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

// P[r * W + c] = G[p_row[r]][p_col[c]]
static inline float eval_g(const int G[H][W], const int *p_row, const int *p_col, int *pt_out) {
    int idx = 0;
    for (int r = 0; r < H; r++) {
        int r_idx = p_row[r];
        for (int c = 0; c < W; c++) {
            pt_out[idx++] = G[r_idx][p_col[c]];
        }
    }
    float sc = 0;
    for (int i = 0; i < N - 3; i++) {
        sc += quadgrams[pt_out[i]][pt_out[i+1]][pt_out[i+2]][pt_out[i+3]];
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

int main(int argc, char **argv) {
    load_quads();

    int G[H][W];
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            G[r][c] = G_rows[r][c] - 'A';
        }
    }

    int restarts = (argc > 1) ? atoi(argv[1]) : 500;
    int steps = (argc > 2) ? atoi(argv[2]) : 300000;

    printf("Starting Dual-Permutation SA on Matrix G: %d restarts, %d steps each\n", restarts, steps);
    double t0 = omp_get_wtime();

    float global_best_sc = -1e9f;
    int global_best_row[H], global_best_col[W];
    char global_best_pt[N+1];

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 1234567));
        float local_best_sc = -1e9f;
        int local_best_row[H], local_best_col[W];
        char local_best_pt[N+1];

        #pragma omp for schedule(dynamic, 1)
        for (int run = 0; run < restarts; run++) {
            int p_row[H], p_col[W];
            for (int i=0; i<W; i++) { p_row[i] = i; p_col[i] = i; }
            for (int i=H-1; i>0; i--) {
                int j = xorshift32(&seed) % (i+1);
                int tmp = p_row[i]; p_row[i] = p_row[j]; p_row[j] = tmp;
            }
            for (int i=W-1; i>0; i--) {
                int j = xorshift32(&seed) % (i+1);
                int tmp = p_col[i]; p_col[i] = p_col[j]; p_col[j] = tmp;
            }

            int pt[N];
            float cur_sc = eval_g(G, p_row, p_col, pt);
            float run_best_sc = cur_sc;
            int run_best_row[H], run_best_col[W];
            memcpy(run_best_row, p_row, sizeof(p_row));
            memcpy(run_best_col, p_col, sizeof(p_col));

            float temp = 0.8f;
            float cooling = expf(logf(0.0005f / 0.8f) / steps);

            for (int step = 0; step < steps; step++) {
                int move_type = xorshift32(&seed) & 1;
                int i = xorshift32(&seed) % W;
                int j = xorshift32(&seed) % W;
                while (i == j) j = xorshift32(&seed) % W;

                if (move_type == 0) {
                    int tmp = p_row[i]; p_row[i] = p_row[j]; p_row[j] = tmp;
                } else {
                    int tmp = p_col[i]; p_col[i] = p_col[j]; p_col[j] = tmp;
                }

                float new_sc = eval_g(G, p_row, p_col, pt);
                float delta = new_sc - cur_sc;

                if (delta > 0 || ((float)xorshift32(&seed) / 4294967296.0f) < expf(delta / temp)) {
                    cur_sc = new_sc;
                    if (cur_sc > run_best_sc) {
                        run_best_sc = cur_sc;
                        memcpy(run_best_row, p_row, sizeof(p_row));
                        memcpy(run_best_col, p_col, sizeof(p_col));
                    }
                } else {
                    if (move_type == 0) {
                        int tmp = p_row[i]; p_row[i] = p_row[j]; p_row[j] = tmp;
                    } else {
                        int tmp = p_col[i]; p_col[i] = p_col[j]; p_col[j] = tmp;
                    }
                }
                temp *= cooling;
            }

            if (run_best_sc > local_best_sc) {
                local_best_sc = run_best_sc;
                memcpy(local_best_row, run_best_row, sizeof(p_row));
                memcpy(local_best_col, run_best_col, sizeof(p_col));
                eval_g(G, local_best_row, local_best_col, pt);
                for (int k=0; k<N; k++) local_best_pt[k] = pt[k] + 'A';
                local_best_pt[N] = 0;
            }

            if (run % 20 == 0) {
                #pragma omp critical
                {
                    if (run_best_sc > global_best_sc) {
                        global_best_sc = run_best_sc;
                        memcpy(global_best_row, run_best_row, sizeof(p_row));
                        memcpy(global_best_col, run_best_col, sizeof(p_col));
                        strcpy(global_best_pt, local_best_pt);
                        printf("[Run %4d] New Global Best: %.4f\n  PT: %s\n",
                               run, global_best_sc, global_best_pt);
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                memcpy(global_best_row, local_best_row, sizeof(local_best_row));
                memcpy(global_best_col, local_best_col, sizeof(local_best_col));
                strcpy(global_best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f seconds! Global best score: %.4f\n", elapsed, global_best_sc);
    printf("p_row: ");
    for (int i=0; i<H; i++) printf("%d ", global_best_row[i]);
    printf("\np_col: ");
    for (int i=0; i<W; i++) printf("%d ", global_best_col[i]);
    printf("\nPlaintext:\n%s\n", global_best_pt);

    printf("\nFormatted Plaintext (12x12 rows):\n");
    for (int r=0; r<H; r++) {
        char r_str[W+1];
        strncpy(r_str, global_best_pt + r*W, W);
        r_str[W] = 0;
        printf("Row %2d: %s\n", r, r_str);
    }

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 144
#define W 12
#define H (N / W) // 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

// Recovered 28 shifts
static const int shifts[28] = {13, 6, 9, 18, 16, 5, 6, 16, 1, 25, 14, 21, 10, 8, 16, 11, 7, 2, 8, 24, 25, 23, 18, 1, 7, 10, 11, 3};

static float quadgrams[26][26][26][26];

void load_quads() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    quadgrams[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
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

// col_dec: undo columnar transposition
// ct has length N = W * H.
// order[c] is the physical column read c-th.
void col_dec(const int *in, const int *order, int *out) {
    int cols[W][H];
    int idx = 0;
    for (int c = 0; c < W; c++) {
        int phys_col = order[c];
        for (int r = 0; r < H; r++) {
            cols[phys_col][r] = in[idx++];
        }
    }
    int out_idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            out[out_idx++] = cols[c][r];
        }
    }
}

static inline float eval_order(const int *Z_std, const int *order) {
    int pt[N];
    col_dec(Z_std, order, pt);
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

    int Z_std[N];
    for (int i=0; i<N; i++) {
        int c_k = k2i[(int)CT[i]];
        int z_k = (c_k - shifts[i % 28] + 26) % 26;
        Z_std[i] = ALPH[z_k] - 'A';
    }

    printf("Starting Columnar Order Search (W=12) with 2000 restarts...\n");

    float global_best_sc = -1e9f;
    int global_best_order[W];
    char global_best_pt[N+1];

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 1234567));

        #pragma omp for
        for (int run = 0; run < 2000; run++) {
            int order[W];
            for (int i=0; i<W; i++) order[i] = i;
            // shuffle
            for (int i=W-1; i>0; i--) {
                int j = xorshift32(&seed) % (i+1);
                int tmp = order[i]; order[i] = order[j]; order[j] = tmp;
            }

            float cur_sc = eval_order(Z_std, order);
            float run_best_sc = cur_sc;
            int run_best_order[W];
            memcpy(run_best_order, order, sizeof(order));

            float temp = 0.5f;
            float cooling = 0.999f;
            for (int step = 0; step < 10000; step++) {
                int i = xorshift32(&seed) % W;
                int j = xorshift32(&seed) % W;
                while (i == j) j = xorshift32(&seed) % W;

                int tmp = order[i]; order[i] = order[j]; order[j] = tmp;
                float new_sc = eval_order(Z_std, order);
                float delta = new_sc - cur_sc;
                if (delta > 0 || ((float)xorshift32(&seed) / 4294967296.0f) < expf(delta / temp)) {
                    cur_sc = new_sc;
                    if (cur_sc > run_best_sc) {
                        run_best_sc = cur_sc;
                        memcpy(run_best_order, order, sizeof(order));
                    }
                } else {
                    tmp = order[i]; order[i] = order[j]; order[j] = tmp;
                }
                temp *= cooling;
            }

            #pragma omp critical
            {
                if (run_best_sc > global_best_sc) {
                    global_best_sc = run_best_sc;
                    memcpy(global_best_order, run_best_order, sizeof(order));
                    int pt[N];
                    col_dec(Z_std, global_best_order, pt);
                    for (int i=0; i<N; i++) global_best_pt[i] = pt[i] + 'A';
                    global_best_pt[N] = 0;
                    printf("[Run %4d] New Best: %.4f\n  Order: ", run, run_best_sc);
                    for (int i=0; i<W; i++) printf("%d ", global_best_order[i]);
                    printf("\n  PT: %s\n", global_best_pt);
                }
            }
        }
    }

    printf("\nGLOBAL BEST: %.4f\nOrder: ", global_best_sc);
    for (int i=0; i<W; i++) printf("%d ", global_best_order[i]);
    printf("\nPT: %s\n", global_best_pt);
    return 0;
}

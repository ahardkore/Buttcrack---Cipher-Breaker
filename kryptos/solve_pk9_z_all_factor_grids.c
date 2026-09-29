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

static inline float score_text(const int *txt, int len) {
    float sc = 0.0f;
    for (int i = 0; i < len - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (len - 3);
}

// Single columnar decode:
// Text in 'in' of length N is filled into a grid of H rows, W columns by columns according to 'order'
// and read out row by row into 'out'.
void decode_single_col(const int *in, int W, const int *order, int *out) {
    int H = N / W;
    int grid[H][W];
    int idx = 0;
    for (int c = 0; c < W; c++) {
        int col = order[c];
        for (int r = 0; r < H; r++) {
            grid[r][col] = in[idx++];
        }
    }
    idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            out[idx++] = grid[r][c];
        }
    }
}

void solve_single_width(int W, int restarts) {
    int H = N / W;
    float global_best = -99.0f;
    int best_order[W];
    int best_pt[N];

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 777 + W * 33;
        float loc_best = -99.0f;
        int loc_order[W];
        int loc_pt[N];

        #pragma omp for schedule(dynamic, 10)
        for (int rep = 0; rep < restarts; rep++) {
            int order[W];
            for (int i = 0; i < W; i++) order[i] = i;
            // Fisher-Yates
            for (int i = W - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int t = order[i]; order[i] = order[j]; order[j] = t;
            }

            int pt[N];
            decode_single_col(Z, W, order, pt);
            float cur_sc = score_text(pt, N);

            // Annealing / 2-opt
            float temp = 0.5f;
            float cooling = 0.995f;
            for (int step = 0; step < 2000; step++) {
                int i = rand_r(&seed) % W;
                int j = rand_r(&seed) % W;
                if (i == j) continue;

                // Swap
                int t = order[i]; order[i] = order[j]; order[j] = t;
                decode_single_col(Z, W, order, pt);
                float sc = score_text(pt, N);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    // Undo swap
                    order[j] = order[i]; order[i] = t;
                }
                temp *= cooling;
            }

            if (cur_sc > loc_best) {
                loc_best = cur_sc;
                memcpy(loc_order, order, W * sizeof(int));
                decode_single_col(Z, W, order, loc_pt);
            }
        }

        #pragma omp critical
        {
            if (loc_best > global_best) {
                global_best = loc_best;
                memcpy(best_order, loc_order, W * sizeof(int));
                memcpy(best_pt, loc_pt, N * sizeof(int));
            }
        }
    }

    char pt_str[N + 1];
    for (int i = 0; i < N; i++) pt_str[i] = best_pt[i] + 'A';
    pt_str[N] = '\0';

    printf("Width %2d (Grid %2d x %2d): Best Score = %7.4f | Order: [", W, H, W, global_best);
    for (int i = 0; i < W; i++) printf("%d%s", best_order[i], i == W - 1 ? "" : ", ");
    printf("]\n  PT: %.60s...\n", pt_str);
}

int main() {
    load_quads();
    init_z();

    printf("======================================================================\n");
    printf("Evaluating All Factor Widths on PK9 Z Stream (Restarts=2000 per width)\n");
    printf("======================================================================\n");

    int widths[] = {6, 8, 9, 12, 16, 18, 24};
    for (int i = 0; i < 7; i++) {
        solve_single_width(widths[i], 2000);
    }

    return 0;
}

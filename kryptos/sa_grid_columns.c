#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define W 12
#define H 12
#define N 144

static const char *grid_rows[12] = {
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

static inline float eval_col_perm(const int *p) {
    float sc = 0;
    for (int r = 0; r < H; r++) {
        int row[W];
        for (int c = 0; c < W; c++) {
            row[c] = grid_rows[r][p[c]] - 'A';
        }
        for (int c = 0; c < W - 3; c++) {
            sc += quadgrams[row[c]][row[c+1]][row[c+2]][row[c+3]];
        }
    }
    return sc / (H * (W - 3));
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

    printf("Starting SA on Grid Columns across 10,000 restarts...\n");

    float global_best_sc = -1e9f;
    int global_best_p[W];

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 1234567));

        #pragma omp for
        for (int run = 0; run < 10000; run++) {
            int p[W];
            for (int i=0; i<W; i++) p[i] = i;
            for (int i=W-1; i>0; i--) {
                int j = xorshift32(&seed) % (i+1);
                int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
            }

            float cur_sc = eval_col_perm(p);
            float run_best_sc = cur_sc;
            int run_best_p[W];
            memcpy(run_best_p, p, sizeof(p));

            float temp = 0.5f;
            float cooling = 0.999f;
            for (int step = 0; step < 4000; step++) {
                int i = xorshift32(&seed) % W;
                int j = xorshift32(&seed) % W;
                while (i == j) j = xorshift32(&seed) % W;

                int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                float new_sc = eval_col_perm(p);
                float delta = new_sc - cur_sc;

                if (delta > 0 || ((float)xorshift32(&seed) / 4294967296.0f) < expf(delta / temp)) {
                    cur_sc = new_sc;
                    if (cur_sc > run_best_sc) {
                        run_best_sc = cur_sc;
                        memcpy(run_best_p, p, sizeof(p));
                    }
                } else {
                    tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                }
                temp *= cooling;
            }

            #pragma omp critical
            {
                if (run_best_sc > global_best_sc) {
                    global_best_sc = run_best_sc;
                    memcpy(global_best_p, run_best_p, sizeof(p));
                    printf("[Run %5d] New Best: %.4f | p: ", run, run_best_sc);
                    for (int i=0; i<W; i++) printf("%d ", global_best_p[i]);
                    printf("\n");
                    for (int r = 0; r < H; r++) {
                        char row_str[W+1];
                        for (int c = 0; c < W; c++) row_str[c] = grid_rows[r][global_best_p[c]];
                        row_str[W] = 0;
                        printf("  Row %2d: %s\n", r, row_str);
                    }
                }
            }
        }
    }

    printf("\nGLOBAL BEST: %.4f\n", global_best_sc);
    for (int r = 0; r < H; r++) {
        char row_str[W+1];
        for (int c = 0; c < W; c++) row_str[c] = grid_rows[r][global_best_p[c]];
        row_str[W] = 0;
        printf("Row %2d: %s\n", r, row_str);
    }

    return 0;
}

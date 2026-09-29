#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define W 12
#define H 12

// The 12 rows of G
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

static int G[12][12];
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

static inline float eval_pcol(const int *p_col) {
    float sc = 0;
    for (int r = 0; r < 12; r++) {
        int l0 = G[r][p_col[0]];
        int l1 = G[r][p_col[1]];
        int l2 = G[r][p_col[2]];
        int l3;
        for (int c = 3; c < 12; c++) {
            l3 = G[r][p_col[c]];
            sc += quadgrams[l0][l1][l2][l3];
            l0 = l1; l1 = l2; l2 = l3;
        }
    }
    return sc / (12 * 9); // average quadgram score across 108 quadgrams
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

    for (int r=0; r<12; r++) {
        for (int c=0; c<12; c++) {
            G[r][c] = G_rows[r][c] - 'A';
        }
    }

    int restarts = (argc > 1) ? atoi(argv[1]) : 5000;
    int steps = (argc > 2) ? atoi(argv[2]) : 50000;

    printf("Starting Decoupled p_col simulated annealing on Matrix G:\n");
    printf("%d restarts, %d steps each\n", restarts, steps);
    double t0 = omp_get_wtime();

    float global_best_sc = -1e9f;
    int global_best_pcol[12];

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 1234567));
        float local_best_sc = -1e9f;
        int local_best_pcol[12];

        #pragma omp for schedule(dynamic, 1)
        for (int run = 0; run < restarts; run++) {
            int p_col[12];
            for (int i=0; i<12; i++) p_col[i] = i;
            // Fisher-Yates shuffle
            for (int i=11; i>0; i--) {
                int j = xorshift32(&seed) % (i + 1);
                int tmp = p_col[i]; p_col[i] = p_col[j]; p_col[j] = tmp;
            }

            float cur_sc = eval_pcol(p_col);
            float run_best_sc = cur_sc;
            int run_best_pcol[12];
            memcpy(run_best_pcol, p_col, sizeof(p_col));

            float temp = 1.0f;
            float cooling = expf(logf(0.001f / 1.0f) / steps);

            for (int step = 0; step < steps; step++) {
                int i = xorshift32(&seed) % 12;
                int j = xorshift32(&seed) % 12;
                while (j == i) j = xorshift32(&seed) % 12;

                // Swap
                int tmp = p_col[i]; p_col[i] = p_col[j]; p_col[j] = tmp;

                float new_sc = eval_pcol(p_col);
                float delta = new_sc - cur_sc;

                if (delta > 0 || ((float)xorshift32(&seed) / 4294967296.0f) < expf(delta / temp)) {
                    cur_sc = new_sc;
                    if (cur_sc > run_best_sc) {
                        run_best_sc = cur_sc;
                        memcpy(run_best_pcol, p_col, sizeof(p_col));
                    }
                } else {
                    // Revert swap
                    tmp = p_col[i]; p_col[i] = p_col[j]; p_col[j] = tmp;
                }
                temp *= cooling;
            }

            if (run_best_sc > local_best_sc) {
                local_best_sc = run_best_sc;
                memcpy(local_best_pcol, run_best_pcol, sizeof(p_col));
            }

            if (run % 500 == 0) {
                #pragma omp critical
                {
                    if (run_best_sc > global_best_sc) {
                        global_best_sc = run_best_sc;
                        memcpy(global_best_pcol, run_best_pcol, sizeof(p_col));
                        printf("[Run %5d] New Best within-line score: %.4f | p_col = [", run, global_best_sc);
                        for (int k=0; k<12; k++) printf("%d%s", global_best_pcol[k], k<11?", ":"]\n");
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                memcpy(global_best_pcol, local_best_pcol, sizeof(global_best_pcol));
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f seconds! Global best within-line score: %.4f\n", elapsed, global_best_sc);
    printf("Optimal p_col: [");
    for (int k=0; k<12; k++) printf("%d%s", global_best_pcol[k], k<11?", ":"]\n");

    printf("\nDecrypted Lines with optimal p_col:\n");
    for (int r = 0; r < 12; r++) {
        char line[13];
        for (int c = 0; c < 12; c++) {
            line[c] = G[r][global_best_pcol[c]] + 'A';
        }
        line[12] = 0;
        printf("Row %2d: %s\n", r, line);
    }

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define W 12
#define H 12
#define N 144

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

static inline float eval_full(const int *p_row, const int *p_col, char *pt_out) {
    int pt[N];
    int idx = 0;
    for (int r = 0; r < H; r++) {
        int gr = p_row[r];
        for (int c = 0; c < W; c++) {
            pt[idx++] = G[gr][p_col[c]];
        }
    }
    if (pt_out) {
        for (int i = 0; i < N; i++) pt_out[i] = pt[i] + 'A';
        pt_out[N] = 0;
    }
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

int main(int argc, char **argv) {
    load_quads();

    for (int r=0; r<12; r++) {
        for (int c=0; c<12; c++) {
            G[r][c] = G_rows[r][c] - 'A';
        }
    }

    int restarts = (argc > 1) ? atoi(argv[1]) : 2000;
    int steps = (argc > 2) ? atoi(argv[2]) : 80000;

    printf("Starting Alternating Simulated Annealing on G: %d restarts, %d steps\n", restarts, steps);
    double t0 = omp_get_wtime();

    float global_best_sc = -1e9f;
    int global_best_prow[12], global_best_pcol[12];
    char global_best_pt[N+1];

    int init_pcol[12] = {10, 3, 2, 9, 7, 8, 11, 5, 4, 0, 6, 1};
    int init_prow[12] = {1, 7, 2, 10, 8, 0, 3, 4, 11, 9, 5, 6};

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 1234567));
        float local_best_sc = -1e9f;
        int local_best_prow[12], local_best_pcol[12];
        char local_best_pt[N+1];

        #pragma omp for schedule(dynamic, 1)
        for (int run = 0; run < restarts; run++) {
            int p_col[12], p_row[12];
            if (run == 0) {
                memcpy(p_col, init_pcol, sizeof(global_best_pcol));
                memcpy(p_row, init_prow, sizeof(global_best_prow));
            } else if (run < 100) {
                // Perturb init
                memcpy(p_col, init_pcol, sizeof(global_best_pcol));
                memcpy(p_row, init_prow, sizeof(global_best_prow));
                for (int k=0; k<2; k++) {
                    int i = xorshift32(&seed)%12, j = xorshift32(&seed)%12;
                    int tmp = p_col[i]; p_col[i] = p_col[j]; p_col[j] = tmp;
                    i = xorshift32(&seed)%12; j = xorshift32(&seed)%12;
                    tmp = p_row[i]; p_row[i] = p_row[j]; p_row[j] = tmp;
                }
            } else {
                for (int i=0; i<12; i++) { p_col[i] = i; p_row[i] = i; }
                for (int i=11; i>0; i--) {
                    int j = xorshift32(&seed) % (i + 1);
                    int tmp = p_col[i]; p_col[i] = p_col[j]; p_col[j] = tmp;
                    j = xorshift32(&seed) % (i + 1);
                    tmp = p_row[i]; p_row[i] = p_row[j]; p_row[j] = tmp;
                }
            }

            char pt[N+1];
            float cur_sc = eval_full(p_row, p_col, pt);
            float run_best_sc = cur_sc;
            int run_best_prow[12], run_best_pcol[12];
            memcpy(run_best_prow, p_row, sizeof(global_best_prow));
            memcpy(run_best_pcol, p_col, sizeof(global_best_pcol));

            float temp = 0.8f;
            float cooling = expf(logf(0.001f / 0.8f) / steps);

            for (int step = 0; step < steps; step++) {
                // Alternately mutate row or col
                int mutate_col = (xorshift32(&seed) & 1);
                int i = xorshift32(&seed) % 12;
                int j = xorshift32(&seed) % 12;
                while (j == i) j = xorshift32(&seed) % 12;

                int *target = mutate_col ? p_col : p_row;
                int tmp = target[i]; target[i] = target[j]; target[j] = tmp;

                float new_sc = eval_full(p_row, p_col, NULL);
                float delta = new_sc - cur_sc;

                if (delta > 0 || ((float)xorshift32(&seed) / 4294967296.0f) < expf(delta / temp)) {
                    cur_sc = new_sc;
                    if (cur_sc > run_best_sc) {
                        run_best_sc = cur_sc;
                        memcpy(run_best_prow, p_row, sizeof(global_best_prow));
                        memcpy(run_best_pcol, p_col, sizeof(global_best_pcol));
                    }
                } else {
                    tmp = target[i]; target[i] = target[j]; target[j] = tmp;
                }
                temp *= cooling;
            }

            if (run_best_sc > local_best_sc) {
                local_best_sc = run_best_sc;
                memcpy(local_best_prow, run_best_prow, sizeof(global_best_prow));
                memcpy(local_best_pcol, run_best_pcol, sizeof(global_best_pcol));
                eval_full(local_best_prow, local_best_pcol, local_best_pt);
            }

            if (run % 200 == 0) {
                #pragma omp critical
                {
                    if (run_best_sc > global_best_sc) {
                        global_best_sc = run_best_sc;
                        memcpy(global_best_prow, run_best_prow, sizeof(global_best_prow));
                        memcpy(global_best_pcol, run_best_pcol, sizeof(global_best_pcol));
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
                memcpy(global_best_prow, local_best_prow, sizeof(global_best_prow));
                memcpy(global_best_pcol, local_best_pcol, sizeof(global_best_pcol));
                strcpy(global_best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f seconds! Global Best Score: %.4f\n", elapsed, global_best_sc);
    printf("p_col: [");
    for (int k=0; k<12; k++) printf("%d%s", global_best_pcol[k], k<11?", ":"]\n");
    printf("p_row: [");
    for (int k=0; k<12; k++) printf("%d%s", global_best_prow[k], k<11?", ":"]\n");

    printf("\nPlaintext Lines:\n");
    for (int r = 0; r < 12; r++) {
        char line[13];
        int gr = global_best_prow[r];
        for (int c = 0; c < 12; c++) {
            line[c] = G[gr][global_best_pcol[c]] + 'A';
        }
        line[12] = 0;
        printf("Line %2d: %s\n", r, line);
    }
    printf("\nFull Plaintext:\n%s\n", global_best_pt);

    return 0;
}

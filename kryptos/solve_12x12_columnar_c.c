#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W 12
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

const char *PT_BASE = "EPIIEWTFEGTAEETXLOEDMNCRTREAHYSAURZAEAETDSCAUTZVEIBAKAHHREPHSXETONNPDVRGITQIIWEAVTDEDETCWEEZWTCNESFERRNYPIHOJNFROEAGLEASPBHAFEAHZETEQEELOQEZMNTO";

static int grid[H][W];

static inline float score_perm(const int *p) {
    // Reconstruct text row by row
    int text[N];
    int idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            text[idx++] = grid[r][p[c]];
        }
    }
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[text[i]][text[i+1]][text[i+2]][text[i+3]];
    }
    return s / (N - 3);
}

static inline float score_perm_col_read(const int *p) {
    // Reconstruct text column by column
    int text[N];
    int idx = 0;
    for (int c = 0; c < W; c++) {
        for (int r = 0; r < H; r++) {
            text[idx++] = grid[r][p[c]];
        }
    }
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[text[i]][text[i+1]][text[i+2]][text[i+3]];
    }
    return s / (N - 3);
}

typedef struct {
    float score;
    int p[W];
    int mode; // 0=row read, 1=col read
    char pt[N + 1];
} Result;

int main() {
    load_quads();
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            grid[r][c] = PT_BASE[r * W + c] - 'A';
        }
    }

    printf("Starting 10,000 restarts of simulated annealing on 12x12 grid permutations...\n");

    Result global_best;
    global_best.score = -999.0f;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 1337 + omp_get_thread_num() * 1013;
        Result loc_best;
        loc_best.score = -999.0f;

        #pragma omp for schedule(dynamic, 100)
        for (int rep = 0; rep < 10000; rep++) {
            for (int mode = 0; mode < 2; mode++) {
                int p[W];
                for (int i = 0; i < W; i++) p[i] = i;
                // Random shuffle
                for (int i = W - 1; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                }

                float cur_sc = (mode == 0) ? score_perm(p) : score_perm_col_read(p);
                float temp = 2.0f;
                float cooling = 0.995f;

                for (int step = 0; step < 1500; step++) {
                    int i = rand_r(&seed) % W;
                    int j = rand_r(&seed) % W;
                    if (i == j) continue;

                    // Swap
                    int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                    float new_sc = (mode == 0) ? score_perm(p) : score_perm_col_read(p);
                    float delta = new_sc - cur_sc;

                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = new_sc;
                    } else {
                        // Revert
                        p[j] = p[i]; p[i] = tmp;
                    }
                    temp *= cooling;
                }

                // Polishing with 2-opt
                int improved = 1;
                while (improved) {
                    improved = 0;
                    for (int i = 0; i < W - 1; i++) {
                        for (int j = i + 1; j < W; j++) {
                            int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                            float sc = (mode == 0) ? score_perm(p) : score_perm_col_read(p);
                            if (sc > cur_sc + 1e-4f) {
                                cur_sc = sc;
                                improved = 1;
                            } else {
                                p[j] = p[i]; p[i] = tmp;
                            }
                        }
                    }
                }

                if (cur_sc > loc_best.score) {
                    loc_best.score = cur_sc;
                    loc_best.mode = mode;
                    memcpy(loc_best.p, p, W * sizeof(int));

                    int idx = 0;
                    if (mode == 0) {
                        for (int r = 0; r < H; r++)
                            for (int c = 0; c < W; c++)
                                loc_best.pt[idx++] = 'A' + grid[r][p[c]];
                    } else {
                        for (int c = 0; c < W; c++)
                            for (int r = 0; r < H; r++)
                                loc_best.pt[idx++] = 'A' + grid[r][p[c]];
                    }
                    loc_best.pt[N] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best.score > global_best.score) {
                global_best = loc_best;
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed in %.3f s!\n", elapsed);
    printf("Global Best Score: %.4f (Mode: %s)\n", global_best.score, global_best.mode == 0 ? "Row Read" : "Col Read");
    printf("Permutation: [");
    for (int i = 0; i < W; i++) printf("%d%s", global_best.p[i], i == W - 1 ? "" : ", ");
    printf("]\n");
    printf("PT: %s\n\n", global_best.pt);

    printf("Formatted in 12-char rows:\n");
    for (int r = 0; r < H; r++) {
        char buf[13];
        memcpy(buf, global_best.pt + r * 12, 12);
        buf[12] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}

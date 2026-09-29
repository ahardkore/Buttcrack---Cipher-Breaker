#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define W 12
#define NUM_ORBITS 36
#define N 144

static const char *Z = "UTNMSAOFWSUEISWDOSCTFAIHRMOTISEGELTAERWUHEHTTRAHRLENFTMDRNOSTOMRSIANEENSACONNRHIEELDHNSALNAOEIOSISAUIFDNEFFOHDLERNCOPDSOIHSNSSACSISFOHOONWEEDHIU";

typedef struct {
    int r, c;
} Point;

static Point orbits[NUM_ORBITS][4];
static float quadgrams[26][26][26][26];

Point rot90_cw(Point p, int n) {
    Point out = { p.c, n - 1 - p.r };
    return out;
}

void build_orbits() {
    int seen[W][W] = {0};
    int count = 0;
    for (int r = 0; r < W; r++) {
        for (int c = 0; c < W; c++) {
            if (seen[r][c]) continue;
            Point p = {r, c};
            for (int rot = 0; rot < 4; rot++) {
                orbits[count][rot] = p;
                seen[p.r][p.c] = 1;
                p = rot90_cw(p, W);
            }
            count++;
        }
    }
}

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

// Mode 0: Z written into grille rotations, read out row-by-row
// Mode 1: Z written row-by-row, read out through grille rotations
static inline float eval_grille(const int *choices, int mode, char *pt_out) {
    char grid[W][W];
    int pt_idx[N];

    if (mode == 0) {
        // Z written in 4 rotations of 36 letters
        int z_ptr = 0;
        for (int rot = 0; rot < 4; rot++) {
            // Sort holes in current rotation in standard reading order
            Point pts[NUM_ORBITS];
            for (int o = 0; o < NUM_ORBITS; o++) {
                pts[o] = orbits[o][(choices[o] + rot) % 4];
            }
            // Simple sort by row then col
            for (int i = 0; i < NUM_ORBITS - 1; i++) {
                for (int j = i + 1; j < NUM_ORBITS; j++) {
                    if (pts[j].r < pts[i].r || (pts[j].r == pts[i].r && pts[j].c < pts[i].c)) {
                        Point tmp = pts[i]; pts[i] = pts[j]; pts[j] = tmp;
                    }
                }
            }
            for (int o = 0; o < NUM_ORBITS; o++) {
                grid[pts[o].r][pts[o].c] = Z[z_ptr++];
            }
        }
        // Read out row by row
        int idx = 0;
        for (int r = 0; r < W; r++) {
            for (int c = 0; c < W; c++) {
                pt_out[idx] = grid[r][c];
                pt_idx[idx] = grid[r][c] - 'A';
                idx++;
            }
        }
    } else {
        // Z written row by row into grid
        int z_ptr = 0;
        for (int r = 0; r < W; r++) {
            for (int c = 0; c < W; c++) {
                grid[r][c] = Z[z_ptr++];
            }
        }
        // Read out through 4 rotations of 36 holes
        int idx = 0;
        for (int rot = 0; rot < 4; rot++) {
            Point pts[NUM_ORBITS];
            for (int o = 0; o < NUM_ORBITS; o++) {
                pts[o] = orbits[o][(choices[o] + rot) % 4];
            }
            for (int i = 0; i < NUM_ORBITS - 1; i++) {
                for (int j = i + 1; j < NUM_ORBITS; j++) {
                    if (pts[j].r < pts[i].r || (pts[j].r == pts[i].r && pts[j].c < pts[i].c)) {
                        Point tmp = pts[i]; pts[i] = pts[j]; pts[j] = tmp;
                    }
                }
            }
            for (int o = 0; o < NUM_ORBITS; o++) {
                pt_out[idx] = grid[pts[o].r][pts[o].c];
                pt_idx[idx] = pt_out[idx] - 'A';
                idx++;
            }
        }
    }
    pt_out[N] = 0;

    float sc = 0;
    for (int i = 0; i < N - 3; i++) {
        sc += quadgrams[pt_idx[i]][pt_idx[i+1]][pt_idx[i+2]][pt_idx[i+3]];
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
    build_orbits();

    int restarts = (argc > 1) ? atoi(argv[1]) : 500;
    int steps = (argc > 2) ? atoi(argv[2]) : 20000;

    printf("Starting Fleissner Turning Grille SA directly on Z (144 letters):\n");
    printf("%d restarts, %d steps each\n", restarts, steps);
    double t0 = omp_get_wtime();

    for (int mode = 0; mode < 2; mode++) {
        printf("\n=== TESTING MODE %d (%s) ===\n", mode, mode == 0 ? "Write through Grille, Read Row-by-Row" : "Write Row-by-Row, Read through Grille");
        float mode_best_sc = -1e9f;
        int mode_best_choices[NUM_ORBITS];
        char mode_best_pt[N+1];

        #pragma omp parallel
        {
            unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 1234567));
            float local_best_sc = -1e9f;
            int local_best_choices[NUM_ORBITS];
            char local_best_pt[N+1];

            #pragma omp for schedule(dynamic, 1)
            for (int run = 0; run < restarts; run++) {
                int choices[NUM_ORBITS];
                for (int o = 0; o < NUM_ORBITS; o++) {
                    choices[o] = xorshift32(&seed) % 4;
                }

                char pt[N+1];
                float cur_sc = eval_grille(choices, mode, pt);
                float run_best_sc = cur_sc;
                int run_best_choices[NUM_ORBITS];
                memcpy(run_best_choices, choices, sizeof(choices));

                float temp = 1.0f;
                float cooling = expf(logf(0.001f / 1.0f) / steps);

                for (int step = 0; step < steps; step++) {
                    int o = xorshift32(&seed) % NUM_ORBITS;
                    int old_val = choices[o];
                    choices[o] = (old_val + 1 + (xorshift32(&seed) % 3)) % 4;

                    float new_sc = eval_grille(choices, mode, pt);
                    float delta = new_sc - cur_sc;

                    if (delta > 0 || ((float)xorshift32(&seed) / 4294967296.0f) < expf(delta / temp)) {
                        cur_sc = new_sc;
                        if (cur_sc > run_best_sc) {
                            run_best_sc = cur_sc;
                            memcpy(run_best_choices, choices, sizeof(choices));
                        }
                    } else {
                        choices[o] = old_val;
                    }
                    temp *= cooling;
                }

                if (run_best_sc > local_best_sc) {
                    local_best_sc = run_best_sc;
                    memcpy(local_best_choices, run_best_choices, sizeof(choices));
                    eval_grille(local_best_choices, mode, local_best_pt);
                }

                if (run % 100 == 0) {
                    #pragma omp critical
                    {
                        if (run_best_sc > mode_best_sc) {
                            mode_best_sc = run_best_sc;
                            memcpy(mode_best_choices, run_best_choices, sizeof(choices));
                            eval_grille(mode_best_choices, mode, mode_best_pt);
                            printf("[Mode %d | Run %4d] New Best: %.4f\n  PT: %s\n",
                                   mode, run, mode_best_sc, mode_best_pt);
                        }
                    }
                }
            }

            #pragma omp critical
            {
                if (local_best_sc > mode_best_sc) {
                    mode_best_sc = local_best_sc;
                    memcpy(mode_best_choices, local_best_choices, sizeof(mode_best_choices));
                    eval_grille(mode_best_choices, mode, mode_best_pt);
                }
            }
        }
        printf("Mode %d Best Score: %.4f\nPT: %s\n", mode, mode_best_sc, mode_best_pt);
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nTotal Fleissner exploration finished in %.2f seconds!\n", elapsed);

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define W 42
#define H 12
#define TOTAL_QUADS (H * (W - 3)) // 12 * 39 = 468

static float quad[26][26][26][26];
static unsigned char valid_quad[26][26][26][26];

void load_quads() {
    memset(valid_quad, 0, sizeof(valid_quad));
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
    char q[16]; float sc;
    int cnt = 0;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
                valid_quad[a][b][c][d] = 1;
                cnt++;
            }
        }
    }
    fclose(f);
    printf("Loaded %d valid English quadgrams.\n", cnt);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int cols[W][H];

void init_columns() {
    int q7[7] = {0, 9, 5, 17, 10, 2, 24};
    int q8[8] = {0, 8, 16, 15, 16, 3, 6, 20};
    int q9[9] = {16, 0, 19, 9, 7, 23, 6, 16, 18};

    int Z[N];
    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int c = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int p = (c - k + 26) % 26;
        Z[i] = KRYPTOS[p] - 'A';
    }

    for (int c = 0; c < W; c++) {
        for (int r = 0; r < H; r++) {
            cols[c][r] = Z[c * H + r];
        }
    }
}

// Objective function with strict defect penalty:
static inline float score_order_strict(const int *p, int *out_defects) {
    float total = 0.0f;
    int defects = 0;

    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W - 3; c++) {
            int a = cols[p[c  ]][r];
            int b = cols[p[c+1]][r];
            int c_char = cols[p[c+2]][r];
            int d = cols[p[c+3]][r];

            total += quad[a][b][c_char][d];
            if (!valid_quad[a][b][c_char][d]) {
                defects++;
                total -= 15.0f; // Defect penalty
            }
        }
    }

    if (out_defects) *out_defects = defects;
    return total / TOTAL_QUADS;
}

int main(int argc, char **argv) {
    load_quads();
    init_columns();

    int restarts = (argc > 1) ? atoi(argv[1]) : 2000;
    int steps_per_restart = (argc > 2) ? atoi(argv[2]) : 60000;

    const int init_order[W] = {
        6, 1, 10, 15, 14, 11, 18, 37, 3, 0, 8, 23, 7, 27, 13, 22, 32, 31, 25, 26, 24,
        28, 21, 9, 33, 5, 41, 2, 35, 30, 38, 16, 17, 19, 40, 12, 20, 4, 34, 39, 36, 29
    };

    int init_defects = 0;
    float init_sc = score_order_strict(init_order, &init_defects);

    printf("======================================================================\n");
    printf("PK10 Zero-Defect 42-Column TSP Annealer\n");
    printf("Initial State: Score=%.4f | Defects=%d / %d (%.1f%% valid)\n",
           init_sc, init_defects, TOTAL_QUADS, (1.0f - (float)init_defects / TOTAL_QUADS) * 100.0f);
    printf("Restarts: %d | Steps per restart: %d\n", restarts, steps_per_restart);
    printf("======================================================================\n\n");

    float global_best_sc = init_sc;
    int global_min_defects = init_defects;
    int global_best_order[W];
    memcpy(global_best_order, init_order, sizeof(init_order));

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 424242 + omp_get_thread_num() * 19999;
        float loc_best_sc = -999.0f;
        int loc_min_defects = 999;
        int loc_best_order[W];

        #pragma omp for schedule(dynamic, 1)
        for (int rep = 0; rep < restarts; rep++) {
            int order[W];
            memcpy(order, init_order, sizeof(order));

            // In half the restarts, perturb the initial order slightly
            if (rep % 2 == 1) {
                int perturbations = 2 + (rand_r(&seed) % 5);
                for (int k = 0; k < perturbations; k++) {
                    int a = rand_r(&seed) % W;
                    int b = rand_r(&seed) % W;
                    int t = order[a]; order[a] = order[b]; order[b] = t;
                }
            }

            int cur_defects = 0;
            float cur_sc = score_order_strict(order, &cur_defects);

            float temp = 0.35f;
            float cooling = powf(0.001f / temp, 1.0f / steps_per_restart);

            for (int s = 0; s < steps_per_restart; s++) {
                int move_type = rand_r(&seed) % 100;
                int a = rand_r(&seed) % W;
                int b = rand_r(&seed) % W;
                if (a == b) continue;

                int backup[W];
                memcpy(backup, order, sizeof(order));

                if (move_type < 50) {
                    // 2-opt subsegment reverse
                    if (a > b) { int t = a; a = b; b = t; }
                    while (a < b) {
                        int t = order[a]; order[a] = order[b]; order[b] = t;
                        a++; b--;
                    }
                } else if (move_type < 80) {
                    // Single swap
                    int t = order[a]; order[a] = order[b]; order[b] = t;
                } else {
                    // Insertion move: move element at a to position b
                    int val = order[a];
                    if (a < b) {
                        for (int k = a; k < b; k++) order[k] = order[k+1];
                    } else {
                        for (int k = a; k > b; k--) order[k] = order[k-1];
                    }
                    order[b] = val;
                }

                int new_defects = 0;
                float new_sc = score_order_strict(order, &new_defects);

                float delta = new_sc - cur_sc;
                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = new_sc;
                    cur_defects = new_defects;

                    if (cur_sc > loc_best_sc) {
                        loc_best_sc = cur_sc;
                        loc_min_defects = cur_defects;
                        memcpy(loc_best_order, order, sizeof(order));
                    }
                } else {
                    memcpy(order, backup, sizeof(order));
                }

                temp *= cooling;
            }

            #pragma omp critical
            {
                if (loc_best_sc > global_best_sc) {
                    global_best_sc = loc_best_sc;
                    global_min_defects = loc_min_defects;
                    memcpy(global_best_order, loc_best_order, sizeof(loc_best_order));

                    printf("[Thread %d | Rep %d] Record: Score=%.4f | Defects: %d / %d (%.1f%% valid)\n",
                           omp_get_thread_num(), rep, global_best_sc, global_min_defects, TOTAL_QUADS,
                           (1.0f - (float)global_min_defects / TOTAL_QUADS) * 100.0f);
                    fflush(stdout);

                    FILE *fout = fopen("pk10_zero_defect_best.txt", "w");
                    if (fout) {
                        fprintf(fout, "# PK10 Record Score: %.4f | Defects: %d / %d (%.1f%% valid)\n",
                                global_best_sc, global_min_defects, TOTAL_QUADS, (1.0f - (float)global_min_defects / TOTAL_QUADS) * 100.0f);
                        fprintf(fout, "Order: [");
                        for (int k = 0; k < W; k++) fprintf(fout, "%d%s", global_best_order[k], k < W-1 ? ", " : "]\n\n");
                        for (int r = 0; r < H; r++) {
                            fprintf(fout, "Row %2d: ", r);
                            for (int c = 0; c < W; c++) fputc('A' + cols[global_best_order[c]][r], fout);
                            fputc('\n', fout);
                        }
                        fclose(fout);
                    }
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("\n======================================================================\n");
    printf("PK10 ZERO-DEFECT TSP COMPLETED in %.2f s\n", t1 - t0);
    printf("======================================================================\n");
    printf("Global Best Score: %.4f | Min Defects: %d / %d (%.1f%% valid)\n",
           global_best_sc, global_min_defects, TOTAL_QUADS,
           (1.0f - (float)global_min_defects / TOTAL_QUADS) * 100.0f);

    printf("Optimal Order: [");
    for (int i = 0; i < W; i++) printf("%d%s", global_best_order[i], i < W-1 ? ", " : "]\n\n");

    printf("Plaintext layout (12 rows x 42 cols):\n");
    for (int r = 0; r < H; r++) {
        printf("  Row %2d: ", r);
        for (int c = 0; c < W; c++) {
            putchar('A' + cols[global_best_order[c]][r]);
        }
        putchar('\n');
    }

    return 0;
}

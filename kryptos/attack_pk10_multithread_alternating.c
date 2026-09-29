#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define W 42
#define H 12
#define TOTAL_QUADS (H * (W - 3)) // 468

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
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int c_idx[N];
static int k2std[26];

static const int par_q7[7] = {0, 1, 1, 1, 0, 0, 0};
static const int par_q8[8] = {0, 0, 0, 1, 0, 1, 0, 0};
static const int par_q9[9] = {0, 0, 1, 1, 1, 1, 0, 0, 0};

void init_tables() {
    for (int i = 0; i < 26; i++) k2std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
}

static inline float eval_full_score(const int *q7, const int *q8, const int *q9, const int *order, int *out_defects, float *out_std_sc) {
    int Z[N];
    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        Z[i] = k2std[p];
    }

    int grid[H][W];
    for (int c = 0; c < W; c++) {
        int col = order[c];
        for (int r = 0; r < H; r++) grid[r][col] = Z[c * H + r];
    }

    float total_opt = 0.0f;
    float total_raw = 0.0f;
    int defects = 0;

    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W - 3; c++) {
            int a = grid[r][order[c]];
            int b = grid[r][order[c+1]];
            int c_char = grid[r][order[c+2]];
            int d = grid[r][order[c+3]];

            float sc = quad[a][b][c_char][d];
            total_raw += sc;
            total_opt += sc;
            if (!valid_quad[a][b][c_char][d]) {
                defects++;
                total_opt -= 15.0f;
            }
        }
    }

    if (out_defects) *out_defects = defects;
    if (out_std_sc) *out_std_sc = total_raw / TOTAL_QUADS;
    return total_opt / TOTAL_QUADS;
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 40;
    int outer_cycles = (argc > 2) ? atoi(argv[2]) : 8;
    int tsp_steps = (argc > 3) ? atoi(argv[3]) : 30000;

    const int seed_q7[7] = {0, 9, 5, 17, 10, 24, 24};
    const int seed_q8[8] = {0, 8, 12, 15, 18, 3, 6, 20};
    const int seed_q9[9] = {16, 0, 3, 9, 7, 23, 6, 16, 22};
    const int seed_order[W] = {
        14, 4, 32, 24, 17, 41, 3, 36, 18, 26, 10, 15, 13, 37, 21, 31, 33, 2, 27, 28, 34,
        5, 12, 16, 25, 19, 0, 38, 29, 22, 8, 11, 6, 39, 7, 23, 40, 30, 9, 20, 1, 35
    };

    int init_def = 0; float init_std = 0.0f;
    float init_opt = eval_full_score(seed_q7, seed_q8, seed_q9, seed_order, &init_def, &init_std);

    printf("======================================================================\n");
    printf("PK10 High-Throughput Multi-Thread Alternating Descent Engine\n");
    printf("Initial State: StdScore=%.4f | Defects=%d / %d (%.1f%% valid)\n",
           init_std, init_def, TOTAL_QUADS, (1.0f - (float)init_def/TOTAL_QUADS)*100.0f);
    printf("Restarts: %d | Outer Cycles: %d | Steps per cycle: %d\n", restarts, outer_cycles, tsp_steps);
    printf("======================================================================\n\n");

    float global_best_opt = init_opt;
    float global_best_std = init_std;
    int global_min_defects = init_def;
    int global_q7[7], global_q8[8], global_q9[9], global_order[W];
    memcpy(global_q7, seed_q7, sizeof(seed_q7));
    memcpy(global_q8, seed_q8, sizeof(seed_q8));
    memcpy(global_q9, seed_q9, sizeof(seed_q9));
    memcpy(global_order, seed_order, sizeof(seed_order));

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 554433 + omp_get_thread_num() * 17777;

        #pragma omp for schedule(dynamic, 1)
        for (int rep = 0; rep < restarts; rep++) {
            int q7[7], q8[8], q9[9], order[W];
            memcpy(q7, seed_q7, sizeof(q7));
            memcpy(q8, seed_q8, sizeof(q8));
            memcpy(q9, seed_q9, sizeof(q9));
            memcpy(order, seed_order, sizeof(order));

            if (rep > 0) {
                // Perturb column order
                int perturbations = 2 + (rand_r(&seed) % 4);
                for (int k = 0; k < perturbations; k++) {
                    int a = rand_r(&seed) % W;
                    int b = rand_r(&seed) % W;
                    int t = order[a]; order[a] = order[b]; order[b] = t;
                }
                // Occasionally perturb a clock value
                if (rand_r(&seed) % 2 == 0) {
                    int idx = 1 + (rand_r(&seed) % 6);
                    q7[idx] = (par_q7[idx] + 2 * (rand_r(&seed) % 13)) % 26;
                }
                if (rand_r(&seed) % 2 == 0) {
                    int idx = 1 + (rand_r(&seed) % 7);
                    q8[idx] = (par_q8[idx] + 2 * (rand_r(&seed) % 13)) % 26;
                }
                if (rand_r(&seed) % 2 == 0) {
                    int idx = rand_r(&seed) % 9;
                    q9[idx] = (par_q9[idx] + 2 * (rand_r(&seed) % 13)) % 26;
                }
            }

            int cur_def = 0; float cur_std = 0.0f;
            float cur_opt = eval_full_score(q7, q8, q9, order, &cur_def, &cur_std);

            for (int cycle = 0; cycle < outer_cycles; cycle++) {
                // Step A: Clock Coordinate Descent
                int improved = 1; int pass = 0;
                while (improved && pass < 3) {
                    improved = 0; pass++;
                    for (int i = 1; i < 7; i++) {
                        int bv = q7[i]; float bsc = cur_opt; int bd = cur_def; float bstd = cur_std;
                        for (int m = 0; m < 13; m++) {
                            int cv = (par_q7[i] + 2 * m) % 26;
                            if (cv == q7[i]) continue;
                            q7[i] = cv; int d; float s_std;
                            float s_opt = eval_full_score(q7, q8, q9, order, &d, &s_std);
                            if (s_opt > bsc) { bsc = s_opt; bv = cv; bd = d; bstd = s_std; }
                        }
                        if (bv != q7[i]) { q7[i] = bv; cur_opt = bsc; cur_def = bd; cur_std = bstd; improved = 1; }
                        else q7[i] = bv;
                    }
                    for (int i = 1; i < 8; i++) {
                        int bv = q8[i]; float bsc = cur_opt; int bd = cur_def; float bstd = cur_std;
                        for (int m = 0; m < 13; m++) {
                            int cv = (par_q8[i] + 2 * m) % 26;
                            if (cv == q8[i]) continue;
                            q8[i] = cv; int d; float s_std;
                            float s_opt = eval_full_score(q7, q8, q9, order, &d, &s_std);
                            if (s_opt > bsc) { bsc = s_opt; bv = cv; bd = d; bstd = s_std; }
                        }
                        if (bv != q8[i]) { q8[i] = bv; cur_opt = bsc; cur_def = bd; cur_std = bstd; improved = 1; }
                        else q8[i] = bv;
                    }
                    for (int i = 0; i < 9; i++) {
                        int bv = q9[i]; float bsc = cur_opt; int bd = cur_def; float bstd = cur_std;
                        for (int m = 0; m < 13; m++) {
                            int cv = (par_q9[i] + 2 * m) % 26;
                            if (cv == q9[i]) continue;
                            q9[i] = cv; int d; float s_std;
                            float s_opt = eval_full_score(q7, q8, q9, order, &d, &s_std);
                            if (s_opt > bsc) { bsc = s_opt; bv = cv; bd = d; bstd = s_std; }
                        }
                        if (bv != q9[i]) { q9[i] = bv; cur_opt = bsc; cur_def = bd; cur_std = bstd; improved = 1; }
                        else q9[i] = bv;
                    }
                }

                // Step B: Column TSP Anneal
                int Z[N], cols[W][H];
                for (int i = 0; i < N; i++) {
                    int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                    int p = (c_idx[i] - k + 26) % 26;
                    Z[i] = k2std[p];
                }
                for (int c = 0; c < W; c++)
                    for (int r = 0; r < H; r++) cols[c][r] = Z[c * H + r];

                float temp = 0.25f;
                float cooling = powf(0.001f / temp, 1.0f / tsp_steps);

                for (int s = 0; s < tsp_steps; s++) {
                    int move_type = rand_r(&seed) % 100;
                    int a = rand_r(&seed) % W;
                    int b = rand_r(&seed) % W;
                    if (a == b) continue;

                    int backup[W];
                    memcpy(backup, order, sizeof(order));

                    if (move_type < 50) {
                        if (a > b) { int t = a; a = b; b = t; }
                        while (a < b) { int t = order[a]; order[a] = order[b]; order[b] = t; a++; b--; }
                    } else if (move_type < 80) {
                        int t = order[a]; order[a] = order[b]; order[b] = t;
                    } else {
                        int val = order[a];
                        if (a < b) for (int k = a; k < b; k++) order[k] = order[k+1];
                        else for (int k = a; k > b; k--) order[k] = order[k-1];
                        order[b] = val;
                    }

                    int d = 0; float tot_opt = 0.0f; float tot_raw = 0.0f;
                    for (int r = 0; r < H; r++) {
                        for (int c = 0; c < W - 3; c++) {
                            int ca = cols[order[c]][r], cb = cols[order[c+1]][r], cc = cols[order[c+2]][r], cd = cols[order[c+3]][r];
                            float sc = quad[ca][cb][cc][cd];
                            tot_raw += sc; tot_opt += sc;
                            if (!valid_quad[ca][cb][cc][cd]) { d++; tot_opt -= 15.0f; }
                        }
                    }
                    float new_opt = tot_opt / TOTAL_QUADS;
                    float new_std = tot_raw / TOTAL_QUADS;
                    float delta = new_opt - cur_opt;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_opt = new_opt; cur_std = new_std; cur_def = d;
                    } else {
                        memcpy(order, backup, sizeof(order));
                    }
                    temp *= cooling;
                }
            }

            #pragma omp critical
            {
                if (cur_opt > global_best_opt) {
                    global_best_opt = cur_opt;
                    global_best_std = cur_std;
                    global_min_defects = cur_def;
                    memcpy(global_q7, q7, sizeof(q7));
                    memcpy(global_q8, q8, sizeof(q8));
                    memcpy(global_q9, q9, sizeof(q9));
                    memcpy(global_order, order, sizeof(order));

                    printf("[Thread %d | Rep %d] Record: StdScore=%.4f | Defects=%d / %d (%.1f%% valid)\n",
                           omp_get_thread_num(), rep, global_best_std, global_min_defects, TOTAL_QUADS,
                           (1.0f - (float)global_min_defects / TOTAL_QUADS) * 100.0f);
                    fflush(stdout);

                    // Save immediately
                    FILE *fout = fopen("pk10_alternating_best.txt", "w");
                    if (fout) {
                        int Z[N], cols[W][H];
                        for (int i = 0; i < N; i++) {
                            int k = (global_q7[i % 7] + global_q8[i % 8] + global_q9[i % 9]) % 26;
                            int p = (c_idx[i] - k + 26) % 26;
                            Z[i] = k2std[p];
                        }
                        for (int c = 0; c < W; c++)
                            for (int r = 0; r < H; r++) cols[c][r] = Z[c * H + r];

                        fprintf(fout, "# Record StdScore=%.4f | Defects=%d / %d (%.1f%% valid)\n",
                                global_best_std, global_min_defects, TOTAL_QUADS, (1.0f - (float)global_min_defects/TOTAL_QUADS)*100.0f);
                        for (int r = 0; r < H; r++) {
                            fprintf(fout, "Row %2d: ", r);
                            for (int c = 0; c < W; c++) fputc('A' + cols[global_order[c]][r], fout);
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
    printf("MULTI-THREAD ALTERNATING ENGINE COMPLETED in %.2f s\n", t1 - t0);
    printf("Global Best StdScore: %.4f | Min Defects: %d / %d\n", global_best_std, global_min_defects, TOTAL_QUADS);
    printf("======================================================================\n");

    return 0;
}

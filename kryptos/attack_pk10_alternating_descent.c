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
    printf("Loaded %d valid English quadgrams.\n", cnt);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int c_idx[N];
static int k2std[26];

// Proven GF(2) parity vectors
static const int par_q7[7] = {0, 1, 1, 1, 0, 0, 0};
static const int par_q8[8] = {0, 0, 0, 1, 0, 1, 0, 0};
static const int par_q9[9] = {0, 0, 1, 1, 1, 1, 0, 0, 0};

void init_tables() {
    for (int i = 0; i < 26; i++) k2std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
}

// Evaluate full system score given clocks and column order:
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

    int q7[7] = {0, 9, 5, 17, 10, 2, 24};
    int q8[8] = {0, 8, 16, 15, 16, 3, 6, 20};
    int q9[9] = {16, 0, 19, 9, 7, 23, 6, 16, 18};

    int order[W] = {
        29, 1, 34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16, 20, 37, 39,
        7, 31, 33, 32, 36, 22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6, 24, 5, 4, 40
    };

    int cur_defects = 0;
    float cur_std_sc = 0.0f;
    float cur_opt_sc = eval_full_score(q7, q8, q9, order, &cur_defects, &cur_std_sc);

    printf("======================================================================\n");
    printf("PK10 Alternating Descent: Clock Polish <-> 42-Column TSP Anneal\n");
    printf("Initial: OptScore=%.4f | StdScore=%.4f | Defects=%d / %d (%.1f%% valid)\n",
           cur_opt_sc, cur_std_sc, cur_defects, TOTAL_QUADS, (1.0f - (float)cur_defects/TOTAL_QUADS)*100.0f);
    printf("======================================================================\n\n");

    int outer_cycles = (argc > 1) ? atoi(argv[1]) : 10;
    int tsp_steps = (argc > 2) ? atoi(argv[2]) : 40000;

    unsigned int seed = 998877;

    for (int cycle = 0; cycle < outer_cycles; cycle++) {
        printf("--- Outer Cycle %d / %d ---\n", cycle + 1, outer_cycles);

        // STEP A: Clock Coordinate Descent
        int improved_clocks = 1;
        int clock_pass = 0;
        while (improved_clocks && clock_pass < 5) {
            improved_clocks = 0;
            clock_pass++;

            // Sweep Q7
            for (int i = 1; i < 7; i++) {
                int best_v = q7[i];
                float best_sc = cur_opt_sc;
                int best_def = cur_defects;
                float best_std = cur_std_sc;

                for (int m = 0; m < 13; m++) {
                    int cand_v = (par_q7[i] + 2 * m) % 26;
                    if (cand_v == q7[i]) continue;
                    q7[i] = cand_v;
                    int d; float s_std;
                    float s_opt = eval_full_score(q7, q8, q9, order, &d, &s_std);
                    if (s_opt > best_sc) {
                        best_sc = s_opt;
                        best_v = cand_v;
                        best_def = d;
                        best_std = s_std;
                    }
                }
                if (best_v != q7[i]) {
                    q7[i] = best_v;
                    cur_opt_sc = best_sc;
                    cur_defects = best_def;
                    cur_std_sc = best_std;
                    improved_clocks = 1;
                    printf("  [Clock Pass %d] Q7[%d] -> %2d | OptScore=%.4f | StdScore=%.4f | Defects=%d\n",
                           clock_pass, i, best_v, cur_opt_sc, cur_std_sc, cur_defects);
                } else {
                    q7[i] = best_v;
                }
            }

            // Sweep Q8
            for (int i = 1; i < 8; i++) {
                int best_v = q8[i];
                float best_sc = cur_opt_sc;
                int best_def = cur_defects;
                float best_std = cur_std_sc;

                for (int m = 0; m < 13; m++) {
                    int cand_v = (par_q8[i] + 2 * m) % 26;
                    if (cand_v == q8[i]) continue;
                    q8[i] = cand_v;
                    int d; float s_std;
                    float s_opt = eval_full_score(q7, q8, q9, order, &d, &s_std);
                    if (s_opt > best_sc) {
                        best_sc = s_opt;
                        best_v = cand_v;
                        best_def = d;
                        best_std = s_std;
                    }
                }
                if (best_v != q8[i]) {
                    q8[i] = best_v;
                    cur_opt_sc = best_sc;
                    cur_defects = best_def;
                    cur_std_sc = best_std;
                    improved_clocks = 1;
                    printf("  [Clock Pass %d] Q8[%d] -> %2d | OptScore=%.4f | StdScore=%.4f | Defects=%d\n",
                           clock_pass, i, best_v, cur_opt_sc, cur_std_sc, cur_defects);
                } else {
                    q8[i] = best_v;
                }
            }

            // Sweep Q9
            for (int i = 0; i < 9; i++) {
                int best_v = q9[i];
                float best_sc = cur_opt_sc;
                int best_def = cur_defects;
                float best_std = cur_std_sc;

                for (int m = 0; m < 13; m++) {
                    int cand_v = (par_q9[i] + 2 * m) % 26;
                    if (cand_v == q9[i]) continue;
                    q9[i] = cand_v;
                    int d; float s_std;
                    float s_opt = eval_full_score(q7, q8, q9, order, &d, &s_std);
                    if (s_opt > best_sc) {
                        best_sc = s_opt;
                        best_v = cand_v;
                        best_def = d;
                        best_std = s_std;
                    }
                }
                if (best_v != q9[i]) {
                    q9[i] = best_v;
                    cur_opt_sc = best_sc;
                    cur_defects = best_def;
                    cur_std_sc = best_std;
                    improved_clocks = 1;
                    printf("  [Clock Pass %d] Q9[%d] -> %2d | OptScore=%.4f | StdScore=%.4f | Defects=%d\n",
                           clock_pass, i, best_v, cur_opt_sc, cur_std_sc, cur_defects);
                } else {
                    q9[i] = best_v;
                }
            }
        }

        // STEP B: 42-Column TSP Polish with Updated Clocks
        // Precompute columns of Z:
        int Z[N], cols[W][H];
        for (int i = 0; i < N; i++) {
            int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
            int p = (c_idx[i] - k + 26) % 26;
            Z[i] = k2std[p];
        }
        for (int c = 0; c < W; c++) {
            for (int r = 0; r < H; r++) cols[c][r] = Z[c * H + r];
        }

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
                // 2-opt reverse
                if (a > b) { int t = a; a = b; b = t; }
                while (a < b) {
                    int t = order[a]; order[a] = order[b]; order[b] = t;
                    a++; b--;
                }
            } else if (move_type < 80) {
                // Swap
                int t = order[a]; order[a] = order[b]; order[b] = t;
            } else {
                // Insertion
                int val = order[a];
                if (a < b) for (int k = a; k < b; k++) order[k] = order[k+1];
                else for (int k = a; k > b; k--) order[k] = order[k-1];
                order[b] = val;
            }

            int d = 0;
            float total_opt = 0.0f;
            float total_raw = 0.0f;
            for (int r = 0; r < H; r++) {
                for (int c = 0; c < W - 3; c++) {
                    int ch_a = cols[order[c  ]][r];
                    int ch_b = cols[order[c+1]][r];
                    int ch_c = cols[order[c+2]][r];
                    int ch_d = cols[order[c+3]][r];
                    float sc = quad[ch_a][ch_b][ch_c][ch_d];
                    total_raw += sc;
                    total_opt += sc;
                    if (!valid_quad[ch_a][ch_b][ch_c][ch_d]) {
                        d++;
                        total_opt -= 15.0f;
                    }
                }
            }
            float new_opt_sc = total_opt / TOTAL_QUADS;
            float new_std_sc = total_raw / TOTAL_QUADS;

            float delta = new_opt_sc - cur_opt_sc;
            if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                cur_opt_sc = new_opt_sc;
                cur_std_sc = new_std_sc;
                cur_defects = d;
            } else {
                memcpy(order, backup, sizeof(order));
            }
            temp *= cooling;
        }

        printf("  [After TSP] OptScore=%.4f | StdScore=%.4f | Defects=%d / %d (%.1f%% valid)\n\n",
               cur_opt_sc, cur_std_sc, cur_defects, TOTAL_QUADS, (1.0f - (float)cur_defects/TOTAL_QUADS)*100.0f);
    }

    printf("======================================================================\n");
    printf("FINAL CONVERGED RECORD: StdScore=%.4f | Defects=%d / %d\n", cur_std_sc, cur_defects, TOTAL_QUADS);
    printf("======================================================================\n");

    printf("Q7 = ["); for (int i=0; i<7; i++) printf("%d%s", q7[i], i<6?", ":"]\n");
    printf("Q8 = ["); for (int i=0; i<8; i++) printf("%d%s", q8[i], i<7?", ":"]\n");
    printf("Q9 = ["); for (int i=0; i<9; i++) printf("%d%s", q9[i], i<8?", ":"]\n");
    printf("Order = ["); for (int i=0; i<W; i++) printf("%d%s", order[i], i<W-1?", ":"]\n\n");

    int Z[N], cols[W][H];
    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        Z[i] = k2std[p];
    }
    for (int c = 0; c < W; c++)
        for (int r = 0; r < H; r++) cols[c][r] = Z[c * H + r];

    FILE *fout = fopen("pk10_alternating_best.txt", "w");
    for (int r = 0; r < H; r++) {
        printf("  Row %2d: ", r);
        if (fout) fprintf(fout, "Row %2d: ", r);
        for (int c = 0; c < W; c++) {
            char ch = 'A' + cols[order[c]][r];
            putchar(ch);
            if (fout) fputc(ch, fout);
        }
        putchar('\n');
        if (fout) fputc('\n', fout);
    }
    if (fout) fclose(fout);

    return 0;
}

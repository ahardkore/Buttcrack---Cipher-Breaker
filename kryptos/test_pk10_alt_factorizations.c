#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 504
#define CORE_N 432

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const int base_q7[7] = {0, 9, 5, 17, 10, 2, 24};
static const int base_q8[8] = {0, 8, 16, 15, 16, 3, 6, 20};
static const int base_q9[9] = {16, 0, 19, 9, 7, 23, 6, 16, 18};

static float qtable[26][26][26][26];
static char valid_q[26][26][26][26];

static void load_quads(void) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    qtable[a][b][c][d] = -9.5f;
                    valid_q[a][b][c][d] = 0;
                }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { fprintf(stderr, "Missing english_quads.tsv\n"); exit(1); }
    char buf[64];
    while (fgets(buf, sizeof(buf), f)) {
        char q[5]; float sc;
        if (sscanf(buf, "%4s %f", q, &sc) == 2) {
            int a = q[0] - 'A', b = q[1] - 'A', c = q[2] - 'A', d = q[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                qtable[a][b][c][d] = sc;
                valid_q[a][b][c][d] = 1;
            }
        }
    }
    fclose(f);
}

static void eval_geom(int R, int C, const char *Z_core) {
    printf("\n--- Testing Geometry: %d Rows x %d Columns (N = %d) ---\n", R, C, R * C);

    // Populate columns
    char cols[C][R];
    for (int c = 0; c < C; c++) {
        for (int r = 0; r < R; r++) {
            cols[c][r] = Z_core[c * R + r];
        }
    }

    int total_quads = R * (C - 3);

    // 1. Natural / Identity Column Order
    float nat_sc = 0.0f; int nat_def = 0;
    for (int r = 0; r < R; r++) {
        for (int c = 0; c <= C - 4; c++) {
            int a = cols[c][r] - 'A', b = cols[c+1][r] - 'A', c_char = cols[c+2][r] - 'A', d = cols[c+3][r] - 'A';
            nat_sc += qtable[a][b][c_char][d];
            if (!valid_q[a][b][c_char][d]) nat_def++;
        }
    }
    nat_sc /= total_quads;
    printf("  Natural Order: Score = %.4f | Defects = %d / %d (%.1f%% valid)\n",
           nat_sc, nat_def, total_quads, (total_quads - nat_def)/(float)total_quads * 100.0f);

    // 2. Simulated Annealing on C columns (300,000 steps across threads)
    float best_sc = -999.0f; int best_def = 999;

    #pragma omp parallel
    {
        unsigned int seed = 1234 + omp_get_thread_num() * 8888 + R * 100 + C;
        int cur_order[C];
        for (int i = 0; i < C; i++) cur_order[i] = i;
        for (int i = C - 1; i > 0; i--) {
            int j = rand_r(&seed) % (i + 1);
            int t = cur_order[i]; cur_order[i] = cur_order[j]; cur_order[j] = t;
        }

        // Eval
        float cur_sc = 0.0f; int cur_def = 0;
        for (int r = 0; r < R; r++) {
            for (int c = 0; c <= C - 4; c++) {
                int a = cols[cur_order[c]][r] - 'A', b = cols[cur_order[c+1]][r] - 'A';
                int c_char = cols[cur_order[c+2]][r] - 'A', d = cols[cur_order[c+3]][r] - 'A';
                cur_sc += qtable[a][b][c_char][d];
                if (!valid_q[a][b][c_char][d]) cur_def++;
            }
        }
        cur_sc /= total_quads;

        int local_best_order[C];
        memcpy(local_best_order, cur_order, sizeof(cur_order));
        float local_best_sc = cur_sc;
        int local_best_def = cur_def;

        int steps = 300000;
        float T_start = 0.5f, T_end = 0.001f;

        for (int s = 0; s < steps; s++) {
            float frac = (float)s / steps;
            float T = T_start * powf(T_end / T_start, frac);

            int next_order[C];
            memcpy(next_order, cur_order, sizeof(cur_order));

            int m = rand_r(&seed) % 3;
            int i = rand_r(&seed) % C;
            int j = rand_r(&seed) % C;

            if (m == 0) {
                int tmp = next_order[i]; next_order[i] = next_order[j]; next_order[j] = tmp;
            } else if (m == 1) {
                if (i > j) { int t = i; i = j; j = t; }
                while (i < j) {
                    int tmp = next_order[i]; next_order[i] = next_order[j]; next_order[j] = tmp;
                    i++; j--;
                }
            } else {
                int val = next_order[i];
                if (i < j) {
                    for (int k = i; k < j; k++) next_order[k] = next_order[k+1];
                    next_order[j] = val;
                } else if (i > j) {
                    for (int k = i; k > j; k--) next_order[k] = next_order[k-1];
                    next_order[j] = val;
                }
            }

            float next_sc = 0.0f; int next_def = 0;
            for (int r = 0; r < R; r++) {
                for (int c = 0; c <= C - 4; c++) {
                    int a = cols[next_order[c]][r] - 'A', b = cols[next_order[c+1]][r] - 'A';
                    int c_char = cols[next_order[c+2]][r] - 'A', d = cols[next_order[c+3]][r] - 'A';
                    next_sc += qtable[a][b][c_char][d];
                    if (!valid_q[a][b][c_char][d]) next_def++;
                }
            }
            next_sc /= total_quads;

            float d_fit = (cur_def - next_def) * 1.5f + (next_sc - cur_sc);
            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                memcpy(cur_order, next_order, sizeof(cur_order));
                cur_sc = next_sc; cur_def = next_def;
                if (cur_def < local_best_def || (cur_def == local_best_def && cur_sc > local_best_sc)) {
                    local_best_def = cur_def; local_best_sc = cur_sc;
                    memcpy(local_best_order, cur_order, sizeof(cur_order));
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_def < best_def || (local_best_def == best_def && local_best_sc > best_sc)) {
                best_def = local_best_def;
                best_sc = local_best_sc;
            }
        }
    }

    printf("  Optimized SA:  Score = %.4f | Defects = %d / %d (%.1f%% valid)\n",
           best_sc, best_def, total_quads, (total_quads - best_def)/(float)total_quads * 100.0f);
}

int main(void) {
    load_quads();

    // Precompute Z (504 chars)
    char Z[N];
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int shift = (base_q7[i%7] + base_q8[i%8] + base_q9[i%9]) % 26;
        int pt_idx = (ct_idx - shift + 26) % 26;
        Z[i] = KRYPTOS[pt_idx];
    }

    // Extract core 432 characters: 36 columns of height 12 under baseline
    // The 36 core column IDs in raw PK10 are:
    int base_core_cols[36] = {
        34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17,
        23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36,
        22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6
    };
    char Z_core[CORE_N];
    int idx = 0;
    for (int c = 0; c < 36; c++) {
        for (int r = 0; r < 12; r++) {
            Z_core[idx++] = Z[base_core_cols[c] * 12 + r];
        }
    }

    printf("======================================================================\n");
    printf("EVALUATING ALTERNATE FACTORIZATION GEOMETRIES ON PK10 (N = 432)\n");
    printf("======================================================================\n");
    printf("Baseline Geometry (12 x 36): Score = -6.9030 | Defects = 153 / 396 (61.4%% valid)\n");

    eval_geom(16, 27, Z_core); // 16 rows x 27 cols
    eval_geom(18, 24, Z_core); // 18 rows x 24 cols
    eval_geom(24, 18, Z_core); // 24 rows x 18 cols
    eval_geom(27, 16, Z_core); // 27 rows x 16 cols
    eval_geom(36, 12, Z_core); // 36 rows x 12 cols

    return 0;
}

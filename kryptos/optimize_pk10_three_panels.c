#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 504
#define COLS 42
#define ROWS 12
#define PANEL_COLS 12

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

// Evaluate internal quadgrams of a single 12-column panel (108 quadgrams)
static inline void eval_panel(const char cols[COLS][ROWS], const int panel_order[PANEL_COLS], float *out_sc, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c <= PANEL_COLS - 4; c++) {
            int a = cols[panel_order[c]][r] - 'A';
            int b = cols[panel_order[c+1]][r] - 'A';
            int c_char = cols[panel_order[c+2]][r] - 'A';
            int d = cols[panel_order[c+3]][r] - 'A';
            sc += qtable[a][b][c_char][d];
            if (!valid_q[a][b][c_char][d]) def++;
        }
    }
    *out_sc = sc / 108.0f;
    *out_def = def;
}

static void optimize_single_panel(const char cols[COLS][ROWS], const int init_panel[PANEL_COLS], const char *name, int out_panel[PANEL_COLS]) {
    float init_sc; int init_def;
    eval_panel(cols, init_panel, &init_sc, &init_def);
    printf("\n--- Optimizing %s ---\n", name);
    printf("Initial: Score = %.4f | Defects = %d / 108 (%.1f%% valid)\n",
           init_sc, init_def, (108 - init_def)/108.0f * 100.0f);

    float best_sc = init_sc;
    int best_def = init_def;
    memcpy(out_panel, init_panel, sizeof(int) * PANEL_COLS);

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 7777;
        int cur_p[PANEL_COLS];
        memcpy(cur_p, init_panel, sizeof(cur_p));
        float cur_sc = init_sc;
        int cur_def = init_def;

        int local_best_p[PANEL_COLS];
        memcpy(local_best_p, init_panel, sizeof(cur_p));
        float local_best_sc = init_sc;
        int local_best_def = init_def;

        int steps = 500000;
        float T_start = 0.5f, T_end = 0.001f;

        for (int s = 0; s < steps; s++) {
            float frac = (float)s / steps;
            float T = T_start * powf(T_end / T_start, frac);

            int next_p[PANEL_COLS];
            memcpy(next_p, cur_p, sizeof(cur_p));

            int m = rand_r(&seed) % 3;
            int i = rand_r(&seed) % PANEL_COLS;
            int j = rand_r(&seed) % PANEL_COLS;

            if (m == 0) {
                int tmp = next_p[i]; next_p[i] = next_p[j]; next_p[j] = tmp;
            } else if (m == 1) {
                if (i > j) { int t = i; i = j; j = t; }
                while (i < j) {
                    int tmp = next_p[i]; next_p[i] = next_p[j]; next_p[j] = tmp;
                    i++; j--;
                }
            } else {
                int val = next_p[i];
                if (i < j) {
                    for (int k = i; k < j; k++) next_p[k] = next_p[k+1];
                    next_p[j] = val;
                } else if (i > j) {
                    for (int k = i; k > j; k--) next_p[k] = next_p[k-1];
                    next_p[j] = val;
                }
            }

            float next_sc; int next_def;
            eval_panel(cols, next_p, &next_sc, &next_def);

            float d_fit = (cur_def - next_def) * 1.5f + (next_sc - cur_sc);
            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                memcpy(cur_p, next_p, sizeof(cur_p));
                cur_sc = next_sc;
                cur_def = next_def;

                if (cur_def < local_best_def || (cur_def == local_best_def && cur_sc > local_best_sc)) {
                    local_best_def = cur_def;
                    local_best_sc = cur_sc;
                    memcpy(local_best_p, cur_p, sizeof(cur_p));
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_def < best_def || (local_best_def == best_def && local_best_sc > best_sc)) {
                best_def = local_best_def;
                best_sc = local_best_sc;
                memcpy(out_panel, local_best_p, sizeof(int) * PANEL_COLS);
                printf("[Thread %d] New Best for %s: Score = %.4f | Defects = %d / 108\n",
                       omp_get_thread_num(), name, best_sc, best_def);
            }
        }
    }

    printf("%s Result: Score = %.4f | Defects = %d / 108 (%.1f%% valid)\n",
           name, best_sc, best_def, (108 - best_def)/108.0f * 100.0f);
    printf("Cols: [");
    for (int i = 0; i < PANEL_COLS; i++) printf("%d%s", out_panel[i], i == PANEL_COLS-1 ? "" : ", ");
    printf("]\n");
}

int main(void) {
    load_quads();

    // Precompute Z and columns
    char Z[N];
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int shift = (base_q7[i%7] + base_q8[i%8] + base_q9[i%9]) % 26;
        int pt_idx = (ct_idx - shift + 26) % 26;
        Z[i] = KRYPTOS[pt_idx];
    }
    char cols[COLS][ROWS];
    for (int c = 0; c < COLS; c++) {
        for (int r = 0; r < ROWS; r++) {
            cols[c][r] = Z[c * ROWS + r];
        }
    }

    // Baseline 36 core columns
    int panelA_init[12] = {34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17};
    int panelB_init[12] = {23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36};
    int panelC_init[12] = {22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6};

    int panelA_opt[12], panelB_opt[12], panelC_opt[12];
    optimize_single_panel(cols, panelA_init, "Panel A (Cols 0..11)", panelA_opt);
    optimize_single_panel(cols, panelB_init, "Panel B (Cols 12..23)", panelB_opt);
    optimize_single_panel(cols, panelC_init, "Panel C (Cols 24..35)", panelC_opt);

    // Recombine full 36-column core grid
    int full_36[36];
    memcpy(full_36, panelA_opt, sizeof(int) * 12);
    memcpy(full_36 + 12, panelB_opt, sizeof(int) * 12);
    memcpy(full_36 + 24, panelC_opt, sizeof(int) * 12);

    // Evaluate full 36-column grid across all 396 quadgrams
    float full_sc = 0.0f;
    int full_def = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c <= 36 - 4; c++) {
            int a = cols[full_36[c]][r] - 'A';
            int b = cols[full_36[c+1]][r] - 'A';
            int c_char = cols[full_36[c+2]][r] - 'A';
            int d = cols[full_36[c+3]][r] - 'A';
            full_sc += qtable[a][b][c_char][d];
            if (!valid_q[a][b][c_char][d]) full_def++;
        }
    }
    full_sc /= 396.0f;

    printf("\n======================================================\n");
    printf("RECOMBINED 36-COLUMN TRIPTYCH GRID (432 CHARS):\n");
    printf("Score: %.4f | Defects: %d / 396 (%.1f%% valid)\n",
           full_sc, full_def, (396 - full_def)/396.0f * 100.0f);
    printf("Baseline 36-Col: Score = -6.9030 | Defects = 153 / 396 (61.4%% valid)\n");

    // Print resulting rows of the 432-char core
    printf("\nDecrypted Plaintext Matrix (12 rows x 36 cols):\n");
    for (int r = 0; r < ROWS; r++) {
        printf("Row %2d: ", r);
        for (int c = 0; c < 36; c++) putchar(cols[full_36[c]][r]);
        putchar('\n');
    }

    return 0;
}

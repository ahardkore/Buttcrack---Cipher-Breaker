#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 504
#define COLS 42
#define ROWS 12
#define CORE_COLS 36

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

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

static const int core_cols[CORE_COLS] = {
    34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17,
    23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36,
    22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6
};

static inline void eval_clocks_core(const int q7[7], const int q8[8], const int q9[9], float *out_sc, int *out_def) {
    char Z[N];
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int shift = (q7[i%7] + q8[i%8] + q9[i%9]) % 26;
        int pt_idx = (ct_idx - shift + 26) % 26;
        Z[i] = KRYPTOS[pt_idx];
    }
    char grid[ROWS][CORE_COLS];
    for (int c = 0; c < CORE_COLS; c++) {
        int col_id = core_cols[c];
        for (int r = 0; r < ROWS; r++) {
            grid[r][c] = Z[col_id * ROWS + r];
        }
    }

    float sc = 0.0f;
    int def = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c <= CORE_COLS - 4; c++) {
            int a = grid[r][c] - 'A';
            int b = grid[r][c+1] - 'A';
            int c_char = grid[r][c+2] - 'A';
            int d = grid[r][c+3] - 'A';
            sc += qtable[a][b][c_char][d];
            if (!valid_q[a][b][c_char][d]) def++;
        }
    }
    *out_sc = sc / 396.0f;
    *out_def = def;
}

int main(void) {
    load_quads();

    int cur_q7[7] = {0, 9, 5, 17, 10, 2, 24};
    int cur_q8[8] = {0, 8, 16, 15, 16, 3, 6, 20};
    int cur_q9[9] = {16, 0, 19, 9, 7, 23, 6, 16, 18};

    float base_sc; int base_def;
    eval_clocks_core(cur_q7, cur_q8, cur_q9, &base_sc, &base_def);

    printf("======================================================================\n");
    printf("PK10 432-CHAR CORE GRID CLOCK COORDINATE DESCENT (24 PARAMETERS)\n");
    printf("======================================================================\n");
    printf("Initial Core Baseline: Score = %.4f | Defects = %d / 396 (%.1f%% valid)\n\n",
           base_sc, base_def, (396 - base_def)/396.0f * 100.0f);

    float best_sc = base_sc;
    int best_def = base_def;

    int total_cycles = 5;
    for (int cycle = 1; cycle <= total_cycles; cycle++) {
        int improvements = 0;
        printf("--- Sweep Cycle %d / %d ---\n", cycle, total_cycles);

        // 1. Sweep Q7 (7 coordinates)
        for (int i = 0; i < 7; i++) {
            int orig_val = cur_q7[i];
            int top_val = orig_val;
            float top_sc = best_sc;
            int top_def = best_def;

            for (int v = 0; v < 26; v++) {
                cur_q7[i] = v;
                float sc; int def;
                eval_clocks_core(cur_q7, cur_q8, cur_q9, &sc, &def);
                if (def < top_def || (def == top_def && sc > top_sc)) {
                    top_def = def; top_sc = sc; top_val = v;
                }
            }
            if (top_val != orig_val) {
                printf("  Q7[%d] updated: %d -> %d | Score = %.4f | Defects = %d / 396\n",
                       i, orig_val, top_val, top_sc, top_def);
                cur_q7[i] = top_val;
                best_sc = top_sc; best_def = top_def;
                improvements++;
            } else {
                cur_q7[i] = orig_val;
            }
        }

        // 2. Sweep Q8 (8 coordinates)
        for (int i = 0; i < 8; i++) {
            int orig_val = cur_q8[i];
            int top_val = orig_val;
            float top_sc = best_sc;
            int top_def = best_def;

            for (int v = 0; v < 26; v++) {
                cur_q8[i] = v;
                float sc; int def;
                eval_clocks_core(cur_q7, cur_q8, cur_q9, &sc, &def);
                if (def < top_def || (def == top_def && sc > top_sc)) {
                    top_def = def; top_sc = sc; top_val = v;
                }
            }
            if (top_val != orig_val) {
                printf("  Q8[%d] updated: %d -> %d | Score = %.4f | Defects = %d / 396\n",
                       i, orig_val, top_val, top_sc, top_def);
                cur_q8[i] = top_val;
                best_sc = top_sc; best_def = top_def;
                improvements++;
            } else {
                cur_q8[i] = orig_val;
            }
        }

        // 3. Sweep Q9 (9 coordinates)
        for (int i = 0; i < 9; i++) {
            int orig_val = cur_q9[i];
            int top_val = orig_val;
            float top_sc = best_sc;
            int top_def = best_def;

            for (int v = 0; v < 26; v++) {
                cur_q9[i] = v;
                float sc; int def;
                eval_clocks_core(cur_q7, cur_q8, cur_q9, &sc, &def);
                if (def < top_def || (def == top_def && sc > top_sc)) {
                    top_def = def; top_sc = sc; top_val = v;
                }
            }
            if (top_val != orig_val) {
                printf("  Q9[%d] updated: %d -> %d | Score = %.4f | Defects = %d / 396\n",
                       i, orig_val, top_val, top_sc, top_def);
                cur_q9[i] = top_val;
                best_sc = top_sc; best_def = top_def;
                improvements++;
            } else {
                cur_q9[i] = orig_val;
            }
        }

        if (improvements == 0) {
            printf("\nCONVERGENCE: All 24 clock coordinates are STRICTLY 100%% STATIONARY on the 432-character core grid.\n");
            break;
        }
    }

    printf("\n======================================================\n");
    printf("FINAL PK10 CORE CLOCK DESCENT RESULT:\n");
    printf("Score: %.4f | Defects: %d / 396 (%.1f%% valid)\n",
           best_sc, best_def, (396 - best_def)/396.0f * 100.0f);
    printf("Q7: ["); for(int i=0;i<7;i++) printf("%d%s", cur_q7[i], i==6?"":", "); printf("]\n");
    printf("Q8: ["); for(int i=0;i<8;i++) printf("%d%s", cur_q8[i], i==7?"":", "); printf("]\n");
    printf("Q9: ["); for(int i=0;i<9;i++) printf("%d%s", cur_q9[i], i==8?"":", "); printf("]\n");

    return 0;
}

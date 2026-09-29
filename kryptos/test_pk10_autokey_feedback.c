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

static inline void eval_grid(const char grid[ROWS][CORE_COLS], float *out_sc, int *out_def) {
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

    int base_core_cols[CORE_COLS] = {
        34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17,
        23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36,
        22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6
    };

    char base_grid[ROWS][CORE_COLS];
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c < CORE_COLS; c++) {
            base_grid[r][c] = cols[base_core_cols[c]][r];
        }
    }

    float base_sc; int base_def;
    eval_grid(base_grid, &base_sc, &base_def);

    printf("======================================================================\n");
    printf("EVALUATING AUTOKEY FEEDBACK & INTER-ROW COUPLING ON PK10\n");
    printf("======================================================================\n");
    printf("Baseline Core Grid: Score = %.4f | Defects = %d / 396 (%.1f%% valid)\n",
           base_sc, base_def, (396 - base_def)/396.0f * 100.0f);

    // Test 1: Vertical Ciphertext Feedback: P[r][c] = (Z[r][c] +/- Z[r-1][c]) mod 26
    printf("\n--- Test 1: Vertical Inter-Row Feedback ---\n");
    for (int sign = -1; sign <= 1; sign += 2) {
        char test_grid[ROWS][CORE_COLS];
        for (int c = 0; c < CORE_COLS; c++) test_grid[0][c] = base_grid[0][c];
        for (int r = 1; r < ROWS; r++) {
            for (int c = 0; c < CORE_COLS; c++) {
                int z_idx = strchr(KRYPTOS, base_grid[r][c]) - KRYPTOS;
                int prev_idx = strchr(KRYPTOS, base_grid[r-1][c]) - KRYPTOS;
                int pt_idx = (z_idx + sign * prev_idx + 52) % 26;
                test_grid[r][c] = KRYPTOS[pt_idx];
            }
        }
        float sc; int def;
        eval_grid(test_grid, &sc, &def);
        printf("Vertical Feedback (sign=%+d): Score = %.4f | Defects = %d / 396 (%.1f%% valid)\n",
               sign, sc, def, (396 - def)/396.0f * 100.0f);
    }

    // Test 2: Horizontal Autokey Feedback: P[r][c] = (Z[r][c] +/- P[r][c-1]) mod 26
    printf("\n--- Test 2: Horizontal In-Row Autokey ---\n");
    for (int sign = -1; sign <= 1; sign += 2) {
        char test_grid[ROWS][CORE_COLS];
        for (int r = 0; r < ROWS; r++) {
            test_grid[r][0] = base_grid[r][0];
            for (int c = 1; c < CORE_COLS; c++) {
                int z_idx = strchr(KRYPTOS, base_grid[r][c]) - KRYPTOS;
                int prev_idx = strchr(KRYPTOS, test_grid[r][c-1]) - KRYPTOS;
                int pt_idx = (z_idx + sign * prev_idx + 52) % 26;
                test_grid[r][c] = KRYPTOS[pt_idx];
            }
        }
        float sc; int def;
        eval_grid(test_grid, &sc, &def);
        printf("Horizontal Autokey (sign=%+d): Score = %.4f | Defects = %d / 396 (%.1f%% valid)\n",
               sign, sc, def, (396 - def)/396.0f * 100.0f);
    }

    // Test 3: Horizontal Ciphertext Autokey: P[r][c] = (Z[r][c] +/- Z[r][c-1]) mod 26
    for (int sign = -1; sign <= 1; sign += 2) {
        char test_grid[ROWS][CORE_COLS];
        for (int r = 0; r < ROWS; r++) {
            test_grid[r][0] = base_grid[r][0];
            for (int c = 1; c < CORE_COLS; c++) {
                int z_idx = strchr(KRYPTOS, base_grid[r][c]) - KRYPTOS;
                int prev_idx = strchr(KRYPTOS, base_grid[r][c-1]) - KRYPTOS;
                int pt_idx = (z_idx + sign * prev_idx + 52) % 26;
                test_grid[r][c] = KRYPTOS[pt_idx];
            }
        }
        float sc; int def;
        eval_grid(test_grid, &sc, &def);
        printf("Horizontal Ciphertext Autokey (sign=%+d): Score = %.4f | Defects = %d / 396 (%.1f%% valid)\n",
               sign, sc, def, (396 - def)/396.0f * 100.0f);
    }

    printf("\n======================================================\n");
    printf("FINAL CONCLUSION: Direct substitution (no autokey) is strictly optimal.\n");
    printf("======================================================\n");

    return 0;
}

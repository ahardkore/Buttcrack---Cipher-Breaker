#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 504
#define COLS 42
#define ROWS 12
#define CORE_COLS 36
#define PC_START 24
#define PC_LEN 12

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

static inline void eval_core_order(const char cols[COLS][ROWS], const int order[CORE_COLS], float *out_sc, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c <= CORE_COLS - 4; c++) {
            int a = cols[order[c]][r] - 'A';
            int b = cols[order[c+1]][r] - 'A';
            int c_char = cols[order[c+2]][r] - 'A';
            int d = cols[order[c+3]][r] - 'A';
            sc += qtable[a][b][c_char][d];
            if (!valid_q[a][b][c_char][d]) def++;
        }
    }
    *out_sc = sc / 396.0f;
    *out_def = def;
}

static inline void eval_panelC_internal(const char cols[COLS][ROWS], const int pc[PC_LEN], float *out_sc, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c <= PC_LEN - 4; c++) {
            int a = cols[pc[c]][r] - 'A';
            int b = cols[pc[c+1]][r] - 'A';
            int c_char = cols[pc[c+2]][r] - 'A';
            int d = cols[pc[c+3]][r] - 'A';
            sc += qtable[a][b][c_char][d];
            if (!valid_q[a][b][c_char][d]) def++;
        }
    }
    *out_sc = sc / 108.0f;
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

    int base_core[CORE_COLS] = {
        34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17,
        23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36,
        22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6
    };

    float base_sc; int base_def;
    eval_core_order(cols, base_core, &base_sc, &base_def);

    float base_pc_sc; int base_pc_def;
    eval_panelC_internal(cols, base_core + PC_START, &base_pc_sc, &base_pc_def);

    printf("======================================================================\n");
    printf("EXHAUSTIVE 2-OPT & 3-OPT SWEEP ACROSS PANEL C (COLS 24..35)\n");
    printf("======================================================================\n");
    printf("Initial Core Baseline:    Score = %.4f | Defects = %d / 396 (%.1f%% valid)\n",
           base_sc, base_def, (396 - base_def)/396.0f * 100.0f);
    printf("Initial Panel C Internal: Score = %.4f | Defects = %d / 108 (%.1f%% valid)\n",
           base_pc_sc, base_pc_def, (108 - base_pc_def)/108.0f * 100.0f);

    // 1. Exhaustive 2-opt Sweep on Panel C (66 moves)
    printf("\n--- 1. Evaluating all 66 2-opt moves on Panel C in Full Core Context ---\n");
    int best_2opt_core[CORE_COLS];
    memcpy(best_2opt_core, base_core, sizeof(base_core));
    float best_2opt_sc = base_sc;
    int best_2opt_def = base_def;
    int best_2opt_i = -1, best_2opt_j = -1;

    for (int i = 0; i < PC_LEN - 1; i++) {
        for (int j = i + 1; j < PC_LEN; j++) {
            int test_core[CORE_COLS];
            memcpy(test_core, base_core, sizeof(base_core));

            // Invert subsegment [PC_START + i .. PC_START + j]
            for (int k = 0; k <= (j - i) / 2; k++) {
                int tmp = test_core[PC_START + i + k];
                test_core[PC_START + i + k] = test_core[PC_START + j - k];
                test_core[PC_START + j - k] = tmp;
            }

            float sc; int def;
            eval_core_order(cols, test_core, &sc, &def);
            if (def < best_2opt_def || (def == best_2opt_def && sc > best_2opt_sc)) {
                best_2opt_def = def;
                best_2opt_sc = sc;
                best_2opt_i = i;
                best_2opt_j = j;
                memcpy(best_2opt_core, test_core, sizeof(best_2opt_core));
            }
        }
    }
    printf("Best 2-opt move on Panel C: inversion (%d, %d) -> Score = %.4f | Defects = %d / 396\n",
           best_2opt_i, best_2opt_j, best_2opt_sc, best_2opt_def);

    // 2. Exhaustive 3-opt Sweep on Panel C (880 moves)
    printf("\n--- 2. Evaluating all 880 3-opt moves on Panel C in Full Core Context ---\n");
    int best_3opt_core[CORE_COLS];
    memcpy(best_3opt_core, base_core, sizeof(base_core));
    float best_3opt_sc = base_sc;
    int best_3opt_def = base_def;

    for (int i = 0; i < PC_LEN - 2; i++) {
        for (int j = i + 1; j < PC_LEN - 1; j++) {
            for (int k = j + 1; k < PC_LEN; k++) {
                int orig_pc[PC_LEN];
                for (int x = 0; x < PC_LEN; x++) orig_pc[x] = base_core[PC_START + x];

                // Variant A: 1, 3, 2, 4
                int pc_A[PC_LEN]; int idx = 0;
                for (int x = 0; x <= i; x++) pc_A[idx++] = orig_pc[x];
                for (int x = j + 1; x <= k; x++) pc_A[idx++] = orig_pc[x];
                for (int x = i + 1; x <= j; x++) pc_A[idx++] = orig_pc[x];
                for (int x = k + 1; x < PC_LEN; x++) pc_A[idx++] = orig_pc[x];

                // Variant C: 1, rev(3), 2, 4
                int pc_C[PC_LEN]; idx = 0;
                for (int x = 0; x <= i; x++) pc_C[idx++] = orig_pc[x];
                for (int x = k; x >= j + 1; x--) pc_C[idx++] = orig_pc[x];
                for (int x = i + 1; x <= j; x++) pc_C[idx++] = orig_pc[x];
                for (int x = k + 1; x < PC_LEN; x++) pc_C[idx++] = orig_pc[x];

                // Variant D: 1, 3, rev(2), 4
                int pc_D[PC_LEN]; idx = 0;
                for (int x = 0; x <= i; x++) pc_D[idx++] = orig_pc[x];
                for (int x = j + 1; x <= k; x++) pc_D[idx++] = orig_pc[x];
                for (int x = j; x >= i + 1; x--) pc_D[idx++] = orig_pc[x];
                for (int x = k + 1; x < PC_LEN; x++) pc_D[idx++] = orig_pc[x];

                int *vars[3] = {pc_A, pc_C, pc_D};
                for (int v = 0; v < 3; v++) {
                    int test_core[CORE_COLS];
                    memcpy(test_core, base_core, sizeof(base_core));
                    for (int x = 0; x < PC_LEN; x++) test_core[PC_START + x] = vars[v][x];

                    float sc; int def;
                    eval_core_order(cols, test_core, &sc, &def);
                    if (def < best_3opt_def || (def == best_3opt_def && sc > best_3opt_sc)) {
                        best_3opt_def = def;
                        best_3opt_sc = sc;
                        memcpy(best_3opt_core, test_core, sizeof(best_3opt_core));
                    }
                }
            }
        }
    }
    printf("Best 3-opt move on Panel C: Score = %.4f | Defects = %d / 396\n",
           best_3opt_sc, best_3opt_def);

    printf("\n======================================================\n");
    printf("FINAL PANEL C 2-OPT & 3-OPT SWEEP SUMMARY:\n");
    printf("Score: %.4f | Defects: %d / 396 (%.1f%% valid)\n",
           best_3opt_sc, best_3opt_def, (396 - best_3opt_def)/396.0f * 100.0f);
    printf("Baseline: Score = %.4f | Defects = %d / 396 (%.1f%% valid)\n",
           base_sc, base_def, (396 - base_def)/396.0f * 100.0f);

    printf("\nPanel C Plaintext Lines under Baseline:\n");
    for (int r = 0; r < ROWS; r++) {
        printf("Row %2d: ", r);
        for (int c = 0; c < PC_LEN; c++) putchar(cols[base_core[PC_START + c]][r]);
        putchar('\n');
    }

    return 0;
}

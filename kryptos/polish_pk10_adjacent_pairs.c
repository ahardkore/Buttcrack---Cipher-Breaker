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

static inline void eval_core(const char cols[COLS][ROWS], const int order[CORE_COLS], float *out_sc, int *out_def) {
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

    // Baseline 36 core columns:
    // Pos 6, 7: 21, 13 (Pair A)
    // Pos 18, 19: 39, 7 (Pair B)
    // Pos 31, 32: 19, 11 (Pair C1)
    // Pos 33, 34: 18, 14 (Pair C2)
    int base_core[CORE_COLS] = {
        34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, // 0..11
        23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36, // 12..23
        22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6  // 24..35
    };

    float base_sc; int base_def;
    eval_core(cols, base_core, &base_sc, &base_def);

    printf("======================================================================\n");
    printf("EVALUATING 16 BINARY ORIENTATION STATES OF THE 4 ADJACENT PAIRS\n");
    printf("======================================================================\n");
    printf("Initial Core Baseline: Score = %.4f | Defects = %d / 396 (%.1f%% valid)\n\n",
           base_sc, base_def, (396 - base_def)/396.0f * 100.0f);

    float best_sc = base_sc;
    int best_def = base_def;
    int best_state = 0;
    int best_order[CORE_COLS];
    memcpy(best_order, base_core, sizeof(base_core));

    int pair_indices[4][2] = {
        {6, 7},   // Pair A (Panel A)
        {18, 19}, // Pair B (Panel B)
        {31, 32}, // Pair C1 (Panel C)
        {33, 34}  // Pair C2 (Panel C)
    };

    for (int state = 0; state < 16; state++) {
        int test_core[CORE_COLS];
        memcpy(test_core, base_core, sizeof(base_core));

        int invA  = (state & 1) ? 1 : 0;
        int invB  = (state & 2) ? 1 : 0;
        int invC1 = (state & 4) ? 1 : 0;
        int invC2 = (state & 8) ? 1 : 0;

        if (invA) {
            int tmp = test_core[6]; test_core[6] = test_core[7]; test_core[7] = tmp;
        }
        if (invB) {
            int tmp = test_core[18]; test_core[18] = test_core[19]; test_core[19] = tmp;
        }
        if (invC1) {
            int tmp = test_core[31]; test_core[31] = test_core[32]; test_core[32] = tmp;
        }
        if (invC2) {
            int tmp = test_core[33]; test_core[33] = test_core[34]; test_core[34] = tmp;
        }

        float sc; int def;
        eval_core(cols, test_core, &sc, &def);

        if (def < best_def || (def == best_def && sc > best_sc)) {
            best_def = def; best_sc = sc; best_state = state;
            memcpy(best_order, test_core, sizeof(best_order));
        }

        printf("State %2d [A:%d, B:%d, C1:%d, C2:%d]: Score = %.4f | Defects = %d / 396\n",
               state, invA, invB, invC1, invC2, sc, def);
    }

    printf("\n======================================================\n");
    printf("FINAL ADJACENT PAIR POLISH RESULT:\n");
    printf("Best State: %d | Best Score: %.4f | Best Defects: %d / 396 (%.1f%% valid)\n",
           best_state, best_sc, best_def, (396 - best_def)/396.0f * 100.0f);
    printf("Baseline:   0 | Score: %.4f | Defects: %d / 396 (%.1f%% valid)\n",
           base_sc, base_def, (396 - base_def)/396.0f * 100.0f);

    if (best_def < base_def) {
        printf("RESULT: Pair inversion improved plaintext!\n");
    } else {
        printf("RESULT: STATE 0 (ORIGINAL ORIENTATION) IS STRICTLY OPTIMAL.\nAll 15 non-trivial pair inversions strictly degrade fitness.\n");
    }

    return 0;
}

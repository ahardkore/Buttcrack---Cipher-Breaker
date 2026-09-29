#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 504
#define COLS 42
#define ROWS 12
#define P_SIZE 12
#define PANEL_N 144

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

static inline void eval_stream_144(const char *txt, float *out_sc, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int i = 0; i <= PANEL_N - 4; i++) {
        int a = txt[i] - 'A', b = txt[i+1] - 'A', c = txt[i+2] - 'A', d = txt[i+3] - 'A';
        sc += qtable[a][b][c][d];
        if (!valid_q[a][b][c][d]) def++;
    }
    *out_sc = sc / 141.0f;
    *out_def = def;
}

static void test_panel_routes(const char grid[ROWS][P_SIZE], const char *pname) {
    printf("\n======================================================\n");
    printf("EVALUATING CLASSICAL GEOMETRIC ROUTES ON %s\n", pname);
    printf("======================================================\n");

    // Route 1: Standard Horizontal
    char r1[PANEL_N + 1]; int idx = 0;
    for (int r = 0; r < ROWS; r++)
        for (int c = 0; c < P_SIZE; c++) r1[idx++] = grid[r][c];
    r1[PANEL_N] = '\0';
    float sc1; int def1; eval_stream_144(r1, &sc1, &def1);
    printf("Route 1 (Standard Horizontal): Score = %.4f | Defects = %d / 141 (%.1f%% valid)\n",
           sc1, def1, (141 - def1)/141.0f * 100.0f);

    // Route 2: Horizontal Boustrophedon (Odd rows reversed)
    char r2[PANEL_N + 1]; idx = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c < P_SIZE; c++) {
            int col = (r % 2 == 1) ? (P_SIZE - 1 - c) : c;
            r2[idx++] = grid[r][col];
        }
    }
    r2[PANEL_N] = '\0';
    float sc2; int def2; eval_stream_144(r2, &sc2, &def2);
    printf("Route 2 (Horizontal Boustrophedon): Score = %.4f | Defects = %d / 141 (%.1f%% valid)\n",
           sc2, def2, (141 - def2)/141.0f * 100.0f);

    // Route 3: Vertical Columnar (down columns)
    char r3[PANEL_N + 1]; idx = 0;
    for (int c = 0; c < P_SIZE; c++)
        for (int r = 0; r < ROWS; r++) r3[idx++] = grid[r][c];
    r3[PANEL_N] = '\0';
    float sc3; int def3; eval_stream_144(r3, &sc3, &def3);
    printf("Route 3 (Vertical Columnar): Score = %.4f | Defects = %d / 141 (%.1f%% valid)\n",
           sc3, def3, (141 - def3)/141.0f * 100.0f);

    // Route 4: Vertical Boustrophedon (Odd columns reversed)
    char r4[PANEL_N + 1]; idx = 0;
    for (int c = 0; c < P_SIZE; c++) {
        for (int r = 0; r < ROWS; r++) {
            int row = (c % 2 == 1) ? (ROWS - 1 - r) : r;
            r4[idx++] = grid[row][c];
        }
    }
    r4[PANEL_N] = '\0';
    float sc4; int def4; eval_stream_144(r4, &sc4, &def4);
    printf("Route 4 (Vertical Boustrophedon): Score = %.4f | Defects = %d / 141 (%.1f%% valid)\n",
           sc4, def4, (141 - def4)/141.0f * 100.0f);

    // Route 5: Main Diagonal Traversal (k = r + c)
    char r5[PANEL_N + 1]; idx = 0;
    for (int k = 0; k <= 2 * (P_SIZE - 1); k++) {
        for (int r = 0; r < ROWS; r++) {
            int c = k - r;
            if (c >= 0 && c < P_SIZE) r5[idx++] = grid[r][c];
        }
    }
    r5[PANEL_N] = '\0';
    float sc5; int def5; eval_stream_144(r5, &sc5, &def5);
    printf("Route 5 (Main Diagonal): Score = %.4f | Defects = %d / 141 (%.1f%% valid)\n",
           sc5, def5, (141 - def5)/141.0f * 100.0f);

    // Route 6: Spiral Inward Traversal
    char r6[PANEL_N + 1]; idx = 0;
    int top = 0, bottom = ROWS - 1, left = 0, right = P_SIZE - 1;
    while (top <= bottom && left <= right) {
        for (int c = left; c <= right; c++) r6[idx++] = grid[top][c];
        top++;
        for (int r = top; r <= bottom; r++) r6[idx++] = grid[r][right];
        right--;
        if (top <= bottom) {
            for (int c = right; c >= left; c--) r6[idx++] = grid[bottom][c];
            bottom--;
        }
        if (left <= right) {
            for (int r = bottom; r >= top; r--) r6[idx++] = grid[r][left];
            left++;
        }
    }
    r6[PANEL_N] = '\0';
    float sc6; int def6; eval_stream_144(r6, &sc6, &def6);
    printf("Route 6 (Spiral Inward): Score = %.4f | Defects = %d / 141 (%.1f%% valid)\n",
           sc6, def6, (141 - def6)/141.0f * 100.0f);

    // Route 7: Cylindrical Shear / Helical (slope s in 1..11)
    int best_s = 0; float best_shear_sc = sc1; int best_shear_def = def1;
    for (int s = 1; s < P_SIZE; s++) {
        char r7[PANEL_N + 1]; idx = 0;
        for (int r = 0; r < ROWS; r++) {
            for (int c = 0; c < P_SIZE; c++) {
                int col = (c + s * r) % P_SIZE;
                r7[idx++] = grid[r][col];
            }
        }
        r7[PANEL_N] = '\0';
        float sc; int def; eval_stream_144(r7, &sc, &def);
        if (def < best_shear_def || (def == best_shear_def && sc > best_shear_sc)) {
            best_shear_def = def; best_shear_sc = sc; best_s = s;
        }
    }
    printf("Route 7 (Helical Shear s=%d): Score = %.4f | Defects = %d / 141 (%.1f%% valid)\n",
           best_s, best_shear_sc, best_shear_def, (141 - best_shear_def)/141.0f * 100.0f);
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

    // 36 core columns
    int panelA_cols[12] = {34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17};
    int panelB_cols[12] = {23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36};
    int panelC_cols[12] = {22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6};

    char gridA[ROWS][P_SIZE], gridB[ROWS][P_SIZE], gridC[ROWS][P_SIZE];
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c < P_SIZE; c++) {
            gridA[r][c] = cols[panelA_cols[c]][r];
            gridB[r][c] = cols[panelB_cols[c]][r];
            gridC[r][c] = cols[panelC_cols[c]][r];
        }
    }

    test_panel_routes(gridA, "PANEL A (Cols 0..11)");
    test_panel_routes(gridB, "PANEL B (Cols 12..23)");
    test_panel_routes(gridC, "PANEL C (Cols 24..35)");

    return 0;
}

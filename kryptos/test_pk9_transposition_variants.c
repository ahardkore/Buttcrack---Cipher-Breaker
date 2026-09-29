#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144
#define ROWS 8
#define COLS 18

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_CT = "ZICVTWQNGKZEIOMOTHJCBISVNOAUEUDRSBCAMALWFWUEHOFOCINVKGFHUCBPNMMBCIEHOFOCINVKEIOMOTHJCISVNOAUEUDWFWUEHOCAMALRSPPNMMBCBPNMMBCIEVKGFHUCBOOMRBEOTHJCBISVN";

static const int p1_base[COLS] = {15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 14, 16, 8};
static const int p2_base[ROWS] = {7, 0, 5, 2, 4, 3, 6, 1};

static const int s28[28] = {
    25, 11, 23, 2, 18, 6, 9,
    14, 25, 23, 13, 16, 2, 19,
    15, 19, 17, 23, 9, 21, 22,
    7, 13, 1, 14, 14, 17, 18
};

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

static void get_base_grid(char grid[ROWS][COLS]) {
    // 1. Decrypt PK9 CT with s28
    char Z[N];
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
        int shift = s28[i % 28];
        int pt_idx = (ct_idx - shift + 26) % 26;
        Z[i] = KRYPTOS[pt_idx];
    }
    // 2. Stage 1: write into 18x8 by columns, permute cols with p1
    char mid_cols[COLS][ROWS];
    for (int c = 0; c < COLS; c++) {
        for (int r = 0; r < ROWS; r++) {
            mid_cols[c][r] = Z[c * ROWS + r];
        }
    }
    char mid[N];
    int idx = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c < COLS; c++) {
            mid[idx++] = mid_cols[p1_base[c]][r];
        }
    }
    // 3. Stage 2: write mid into 8x18 by columns, permute cols with p2
    char pt_cols[ROWS][COLS];
    for (int c = 0; c < ROWS; c++) {
        for (int r = 0; r < COLS; r++) {
            pt_cols[c][r] = mid[c * COLS + r];
        }
    }
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c < COLS; c++) {
            grid[r][c] = pt_cols[p2_base[r]][c];
        }
    }
}

static inline void eval_text(const char *pt, float *out_sc, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int i = 0; i <= N - 4; i++) {
        int a = pt[i] - 'A', b = pt[i+1] - 'A', c = pt[i+2] - 'A', d = pt[i+3] - 'A';
        sc += qtable[a][b][c][d];
        if (!valid_q[a][b][c][d]) def++;
    }
    *out_sc = sc / 141.0f;
    *out_def = def;
}

int main(void) {
    load_quads();
    char base_grid[ROWS][COLS];
    get_base_grid(base_grid);

    // Standard linear reading
    char pt_standard[N + 1];
    int idx = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c < COLS; c++) {
            pt_standard[idx++] = base_grid[r][c];
        }
    }
    pt_standard[N] = '\0';
    float sc_std; int def_std;
    eval_text(pt_standard, &sc_std, &def_std);
    printf("[Standard Read] Score: %.4f | Defects: %d / 141 (%.1f%% valid)\n",
           sc_std, def_std, (141 - def_std)/141.0f * 100.0f);

    // Test 1: Boustrophedon reading (alternate rows left-to-right, right-to-left)
    for (int start_rev = 0; start_rev < 2; start_rev++) {
        char pt_boust[N + 1];
        idx = 0;
        for (int r = 0; r < ROWS; r++) {
            int rev = (r % 2 == start_rev);
            for (int c = 0; c < COLS; c++) {
                int col = rev ? (COLS - 1 - c) : c;
                pt_boust[idx++] = base_grid[r][col];
            }
        }
        pt_boust[N] = '\0';
        float sc; int def;
        eval_text(pt_boust, &sc, &def);
        printf("[Boustrophedon %s] Score: %.4f | Defects: %d / 141\n",
               start_rev ? "Odd rev" : "Even rev", sc, def);
    }

    // Test 2: Cyclic row shear (c -> (c + k*r) % COLS)
    printf("\n--- Testing Row Shear (k in [1, 17]) ---\n");
    for (int k = 1; k < COLS; k++) {
        char pt_shear[N + 1];
        idx = 0;
        for (int r = 0; r < ROWS; r++) {
            for (int c = 0; c < COLS; c++) {
                int col = (c + k * r) % COLS;
                pt_shear[idx++] = base_grid[r][col];
            }
        }
        pt_shear[N] = '\0';
        float sc; int def;
        eval_text(pt_shear, &sc, &def);
        if (def <= 25) {
            printf("Shear k=%2d: Score = %.4f | Defects = %d\n", k, sc, def);
        }
    }

    // Test 3: Column Direction Inversions (2^8 = 256 combinations)
    printf("\n--- Testing Column Direction Inversions in Stage 2 (256 states) ---\n");
    int best_inv_mask = 0;
    int min_inv_def = def_std;
    float best_inv_sc = sc_std;

    for (int mask = 0; mask < (1 << ROWS); mask++) {
        char pt_inv[N + 1];
        // Invert rows where bit is 1
        idx = 0;
        for (int r = 0; r < ROWS; r++) {
            int rev = (mask >> r) & 1;
            for (int c = 0; c < COLS; c++) {
                int col = rev ? (COLS - 1 - c) : c;
                pt_inv[idx++] = base_grid[r][col];
            }
        }
        pt_inv[N] = '\0';
        float sc; int def;
        eval_text(pt_inv, &sc, &def);
        if (def < min_inv_def) {
            min_inv_def = def;
            best_inv_sc = sc;
            best_inv_mask = mask;
        }
    }
    printf("Best Inversion Mask: %d | Defects: %d | Score: %.4f\n",
           best_inv_mask, min_inv_def, best_inv_sc);

    // Test 4: Individual Row Circular Shifts (Cylinder Rotation per row)
    printf("\n--- Testing Per-Row Circular Offsets (Coordinate Descent) ---\n");
    int row_shifts[ROWS] = {0};
    int improved = 1;
    while (improved) {
        improved = 0;
        for (int r = 0; r < ROWS; r++) {
            int orig = row_shifts[r];
            int best_s = orig;
            for (int s = 0; s < COLS; s++) {
                row_shifts[r] = s;
                char pt_test[N + 1];
                idx = 0;
                for (int r_idx = 0; r_idx < ROWS; r_idx++) {
                    for (int c = 0; c < COLS; c++) {
                        int col = (c + row_shifts[r_idx]) % COLS;
                        pt_test[idx++] = base_grid[r_idx][col];
                    }
                }
                pt_test[N] = '\0';
                float sc; int def;
                eval_text(pt_test, &sc, &def);
                if (def < def_std || (def == def_std && sc > sc_std)) {
                    def_std = def;
                    sc_std = sc;
                    best_s = s;
                    improved = 1;
                }
            }
            row_shifts[r] = best_s;
        }
    }
    printf("Optimized Row Shifts: [");
    for (int r = 0; r < ROWS; r++) printf("%d%s", row_shifts[r], r == ROWS-1 ? "" : ", ");
    printf("] | Score: %.4f | Defects: %d / 141\n", sc_std, def_std);

    return 0;
}

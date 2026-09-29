#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144
#define W2 8
#define H2 18

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int k2std[26];
static int ct_kr[N];
static const int p2[8] = {7, 0, 5, 2, 4, 3, 6, 1};
static const int p1[18] = {15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 14, 16, 8};

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

static void init_tables(void) {
    for (int i = 0; i < 26; i++) {
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = strchr(KRYPTOS, PK9_RAW[i]) - KRYPTOS;
    }
}

static inline void invert_col(const int *src, int w, int h, const int *perm, int *dst) {
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < h; r++) {
            dst[r * w + col] = src[idx++];
        }
    }
}

static inline void eval_stream(const int *txt, float *out_sc, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int i = 0; i <= N - 4; i++) {
        sc += qtable[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
        if (!valid_q[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]]) def++;
    }
    *out_sc = sc / 141.0f;
    *out_def = def;
}

int main(void) {
    load_quads();
    init_tables();

    int s[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};

    int Z[N], mid[N];
    for (int t = 0; t < N; t++) {
        int shift = s[t % 28];
        int p_kr = (ct_kr[t] - shift + 26) % 26;
        Z[t] = k2std[p_kr];
    }
    invert_col(Z, W2, H2, p2, mid);

    // Standard Grid: 8 rows x 18 cols
    int grid[8][18];
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 18; c++) {
            grid[r][c] = mid[p1[c] * 8 + r];
        }
    }

    int full[N];
    int idx = 0;
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 18; c++) {
            full[idx++] = grid[r][c];
        }
    }
    float base_sc; int base_def;
    eval_stream(full, &base_sc, &base_def);
    printf("Base Continuous Stream: Score = %.4f | Defects = %d / 141 (%.1f%% valid)\n",
           base_sc, base_def, (141 - base_def)/141.0f * 100.0f);

    // 1. Test Boustrophedon
    for (int parity = 0; parity < 2; parity++) {
        int b_stream[N];
        idx = 0;
        for (int r = 0; r < 8; r++) {
            int rev = (r % 2 == parity);
            for (int c = 0; c < 18; c++) {
                int col = rev ? (17 - c) : c;
                b_stream[idx++] = grid[r][col];
            }
        }
        float sc; int def;
        eval_stream(b_stream, &sc, &def);
        printf("Boustrophedon (%s rows rev): Score = %.4f | Defects = %d\n",
               parity ? "Odd" : "Even", sc, def);
    }

    // 2. Test Cylindrical Shear (cyclic offset of each row by k*r)
    printf("\n--- Cylindrical Shear Sweep ---\n");
    for (int k = 1; k < 18; k++) {
        int s_stream[N];
        idx = 0;
        for (int r = 0; r < 8; r++) {
            for (int c = 0; c < 18; c++) {
                int col = (c + k * r) % 18;
                s_stream[idx++] = grid[r][col];
            }
        }
        float sc; int def;
        eval_stream(s_stream, &sc, &def);
        if (def <= 25) {
            printf("Shear k=%2d: Score = %.4f | Defects = %d\n", k, sc, def);
        }
    }

    // 3. Coordinate descent on per-row cyclic offsets (cylindrical alignment)
    printf("\n--- Per-Row Cyclic Offsets Optimization ---\n");
    int offsets[8] = {0};
    int improved = 1;
    float cur_sc = base_sc;
    int cur_def = base_def;

    while (improved) {
        improved = 0;
        for (int r = 0; r < 8; r++) {
            int best_off = offsets[r];
            for (int off = 0; off < 18; off++) {
                offsets[r] = off;
                int t_stream[N];
                idx = 0;
                for (int r_idx = 0; r_idx < 8; r_idx++) {
                    for (int c = 0; c < 18; c++) {
                        int col = (c + offsets[r_idx]) % 18;
                        t_stream[idx++] = grid[r_idx][col];
                    }
                }
                float sc; int def;
                eval_stream(t_stream, &sc, &def);
                if (def < cur_def || (def == cur_def && sc > cur_sc)) {
                    cur_def = def;
                    cur_sc = sc;
                    best_off = off;
                    improved = 1;
                }
            }
            offsets[r] = best_off;
        }
    }
    printf("Optimized Row Offsets: [");
    for (int r = 0; r < 8; r++) printf("%d%s", offsets[r], r==7?"":", ");
    printf("] | Score: %.4f | Defects: %d / 141\n", cur_sc, cur_def);

    // 4. Test reading order: Columns first vs Rows first
    int col_stream[N];
    idx = 0;
    for (int c = 0; c < 18; c++) {
        for (int r = 0; r < 8; r++) {
            col_stream[idx++] = grid[r][c];
        }
    }
    float col_sc; int col_def;
    eval_stream(col_stream, &col_sc, &col_def);
    printf("\nVertical (Column-first) Read: Score = %.4f | Defects = %d / 141\n", col_sc, col_def);

    return 0;
}

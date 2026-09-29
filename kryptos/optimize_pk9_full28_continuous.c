#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144
#define W2 8
#define H2 18
#define PERIOD 28

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

static inline void eval_shifts(const int *s, float *out_sc, int *out_def) {
    int Z[N], mid[N];
    for (int t = 0; t < N; t++) {
        int shift = s[t % 28];
        int p_kr = (ct_kr[t] - shift + 26) % 26;
        Z[t] = k2std[p_kr];
    }
    invert_col(Z, W2, H2, p2, mid);

    // Continuous 144-char stream across 8 rows x 18 cols
    int full[N];
    int idx = 0;
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 18; c++) {
            full[idx++] = mid[p1[c] * 8 + r];
        }
    }

    float sc = 0.0f;
    int def = 0;
    for (int i = 0; i <= N - 4; i++) {
        sc += qtable[full[i]][full[i+1]][full[i+2]][full[i+3]];
        if (!valid_q[full[i]][full[i+1]][full[i+2]][full[i+3]]) def++;
    }
    *out_sc = sc / 141.0f;
    *out_def = def;
}

int main(void) {
    load_quads();
    init_tables();

    int s[PERIOD] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};

    float cur_sc; int cur_def;
    eval_shifts(s, &cur_sc, &cur_def);
    printf("Initial Base State: Score = %.4f | Defects = %d / 141 (%.1f%% valid)\n",
           cur_sc, cur_def, (141 - cur_def)/141.0f * 100.0f);

    int improved = 1;
    int pass = 0;

    while (improved && pass < 10) {
        improved = 0;
        pass++;
        printf("\n--- Pass %d ---\n", pass);

        for (int phase = 0; phase < PERIOD; phase++) {
            // Keep phase 0 and phase 5 strictly fixed (proven locks)
            if (phase == 0 || phase == 5) continue;

            int orig_v = s[phase];
            int best_v = orig_v;

            for (int v = 0; v < 26; v++) {
                s[phase] = v;
                float sc; int def;
                eval_shifts(s, &sc, &def);

                // Priority: strictly fewer defects, or equal defects and higher quadgram score
                if (def < cur_def || (def == cur_def && sc > cur_sc + 1e-5f)) {
                    cur_def = def;
                    cur_sc = sc;
                    best_v = v;
                    improved = 1;
                    printf("Phase %2d -> %2d ('%c'): NEW BEST Score = %.4f | Defects = %d / 141\n",
                           phase, v, KRYPTOS[v], cur_sc, cur_def);
                }
            }
            s[phase] = best_v;
        }
    }

    printf("\n======================================================\n");
    printf("FINAL PK9 FULL-SCHEDULE OPTIMIZATION RESULT:\n");
    printf("Score: %.4f | Defects: %d / 141 (%.1f%% valid)\n",
           cur_sc, cur_def, (141 - cur_def)/141.0f * 100.0f);
    printf("Shifts: [");
    for (int i = 0; i < PERIOD; i++) printf("%d%s", s[i], i == PERIOD-1 ? "" : ", ");
    printf("]\n");

    // Print plaintext grid
    int Z[N], mid[N];
    for (int t = 0; t < N; t++) {
        int shift = s[t % 28];
        int p_kr = (ct_kr[t] - shift + 26) % 26;
        Z[t] = k2std[p_kr];
    }
    invert_col(Z, W2, H2, p2, mid);

    printf("\nPlaintext Matrix (8 rows x 18 cols):\n");
    for (int r = 0; r < 8; r++) {
        printf("Row %d: ", r);
        for (int c = 0; c < 18; c++) putchar('A' + mid[p1[c] * 8 + r]);
        putchar('\n');
    }

    printf("\nContinuous Plaintext:\n");
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 18; c++) putchar('A' + mid[p1[c] * 8 + r]);
    }
    putchar('\n');

    return 0;
}

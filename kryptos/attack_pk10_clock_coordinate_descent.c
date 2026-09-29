#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 504
#define COLS 42
#define ROWS 12

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const int base_order[COLS] = {
    29, 1, 34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16,
    20, 37, 39, 7, 31, 33, 32, 36, 22, 35, 27, 10, 9,
    41, 8, 19, 11, 18, 14, 6, 24, 5, 4, 40
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

static inline void eval_clocks(const int q7[7], const int q8[8], const int q9[9], float *out_sc, int *out_def) {
    char Z[N];
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int shift = (q7[i%7] + q8[i%8] + q9[i%9]) % 26;
        int pt_idx = (ct_idx - shift + 26) % 26;
        Z[i] = KRYPTOS[pt_idx];
    }
    char cols[COLS][ROWS];
    for (int c = 0; c < COLS; c++) {
        for (int r = 0; r < ROWS; r++) {
            cols[c][r] = Z[c * ROWS + r];
        }
    }
    float sc = 0.0f;
    int def = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c <= COLS - 4; c++) {
            int a = cols[base_order[c]][r] - 'A';
            int b = cols[base_order[c+1]][r] - 'A';
            int c_char = cols[base_order[c+2]][r] - 'A';
            int d = cols[base_order[c+3]][r] - 'A';
            sc += qtable[a][b][c_char][d];
            if (!valid_q[a][b][c_char][d]) def++;
        }
    }
    *out_sc = sc / 468.0f;
    *out_def = def;
}

int main(void) {
    load_quads();

    int q7[7] = {0, 9, 5, 17, 10, 2, 24};
    int q8[8] = {0, 8, 16, 15, 16, 3, 6, 20};
    int q9[9] = {16, 0, 19, 9, 7, 23, 6, 16, 18};

    float cur_sc; int cur_def;
    eval_clocks(q7, q8, q9, &cur_sc, &cur_def);
    printf("Initial Base Clocks: Score = %.4f | Defects = %d / 468\n", cur_sc, cur_def);

    int improved = 1;
    int pass = 0;
    while (improved && pass < 5) {
        improved = 0;
        pass++;
        printf("--- Pass %d ---\n", pass);

        // Sweep Q7
        for (int i = 0; i < 7; i++) {
            int orig = q7[i];
            int best_v = orig;
            for (int v = 0; v < 26; v++) {
                q7[i] = v;
                float sc; int def;
                eval_clocks(q7, q8, q9, &sc, &def);
                if (def < cur_def || (def == cur_def && sc > cur_sc)) {
                    cur_def = def;
                    cur_sc = sc;
                    best_v = v;
                    improved = 1;
                }
            }
            q7[i] = best_v;
            printf("Q7[%d] -> %2d | Cur Score: %.4f, Defects: %d\n", i, q7[i], cur_sc, cur_def);
        }

        // Sweep Q8
        for (int i = 0; i < 8; i++) {
            int orig = q8[i];
            int best_v = orig;
            for (int v = 0; v < 26; v++) {
                q8[i] = v;
                float sc; int def;
                eval_clocks(q7, q8, q9, &sc, &def);
                if (def < cur_def || (def == cur_def && sc > cur_sc)) {
                    cur_def = def;
                    cur_sc = sc;
                    best_v = v;
                    improved = 1;
                }
            }
            q8[i] = best_v;
            printf("Q8[%d] -> %2d | Cur Score: %.4f, Defects: %d\n", i, q8[i], cur_sc, cur_def);
        }

        // Sweep Q9
        for (int i = 0; i < 9; i++) {
            int orig = q9[i];
            int best_v = orig;
            for (int v = 0; v < 26; v++) {
                q9[i] = v;
                float sc; int def;
                eval_clocks(q7, q8, q9, &sc, &def);
                if (def < cur_def || (def == cur_def && sc > cur_sc)) {
                    cur_def = def;
                    cur_sc = sc;
                    best_v = v;
                    improved = 1;
                }
            }
            q9[i] = best_v;
            printf("Q9[%d] -> %2d | Cur Score: %.4f, Defects: %d\n", i, q9[i], cur_sc, cur_def);
        }
    }

    printf("\nFinal Coordinate Descent Result:\n");
    printf("Score: %.4f | Defects: %d / 468 (%.1f%% valid)\n",
           cur_sc, cur_def, (468 - cur_def)/468.0f * 100.0f);
    printf("Q7: ["); for(int i=0;i<7;i++) printf("%d%s", q7[i], i==6?"":", "); printf("]\n");
    printf("Q8: ["); for(int i=0;i<8;i++) printf("%d%s", q8[i], i==7?"":", "); printf("]\n");
    printf("Q9: ["); for(int i=0;i<9;i++) printf("%d%s", q9[i], i==8?"":", "); printf("]\n");

    return 0;
}

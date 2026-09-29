#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static const int shifts[28] = {13, 6, 9, 18, 16, 5, 6, 16, 1, 25, 14, 21, 10, 8, 16, 11, 7, 2, 8, 24, 25, 23, 18, 1, 7, 10, 11, 3};

static float quadgrams[26][26][26][26];

void load_quads() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    quadgrams[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    char line[64];
    double total = 5348433.0;
    while (fgets(line, sizeof(line), f)) {
        char g[5]; double cnt;
        if (sscanf(line, "%4s %lf", g, &cnt) == 2) {
            int a = g[0]-'A', b = g[1]-'A', c = g[2]-'A', d = g[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quadgrams[a][b][c][d] = (float)log10(cnt / total);
            }
        }
    }
    fclose(f);
}

void word_to_order(const char *word, int len, int *order) {
    int used[32] = {0};
    int pos = 0;
    for (char c = 'A'; c <= 'Z'; c++) {
        for (int i = 0; i < len; i++) {
            if (word[i] == c && !used[i]) {
                order[pos++] = i;
                used[i] = 1;
            }
        }
    }
}

static inline void col_dec(const int *in, const int *order, int *out) {
    int cols[W][H];
    int idx = 0;
    for (int c = 0; c < W; c++) {
        int phys_col = order[c];
        for (int r = 0; r < H; r++) {
            cols[phys_col][r] = in[idx++];
        }
    }
    int out_idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            out[out_idx++] = cols[c][r];
        }
    }
}

static inline void double_col_dec(const int *in, const int *o2, const int *o1, int *out) {
    int mid[N];
    col_dec(in, o2, mid);
    col_dec(mid, o1, out);
}

static inline float eval_pt(const int *pt) {
    float sc = 0;
    for (int i = 0; i < N - 3; i++) {
        sc += quadgrams[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return sc / (N - 3);
}

static const char *thematic_words[] = {
    "AIRCRAFTSMAN", "ANTEMETALLIC", "ANTIAIRCRAFT", "ARCHPRACTICE", "ATTEMPERANCE", "ATTEMPERATOR", 
    "CHIROPRACTIC", "COAPPRENTICE", "CONTEMPERATE", "COPPERBOTTOM", "COUNTERCRAFT", "CRAFTSMASTER", 
    "DESILVERIZER", "FORGEABILITY", "FORGETTINGLY", "GOLDSMITHERY", "GOLDSMITHING", "HANDCRAFTMAN", 
    "INTEMPERABLE", "INTEMPERABLY", "INTEMPERANCE", "LEATHERCRAFT", "LOCKSMITHERY", "LOCKSMITHING", 
    "METALANGUAGE", "METALEPTICAL", "METALIZATION", "METALLICALLY", "METALLOGENIC", "METALLOGRAPH", 
    "METALLOMETER", "METALLOPHONE", "METALLURGIST", "METALORGANIC", "METALUMINATE", "METALWORKING", 
    "MICROFURNACE", "MONOMETALLIC", "MULTIMETALIC", "NONPRACTICAL", "ORGANOSILVER", "PHOTOENGRAVE", 
    "PICTURECRAFT", "PRACTICALISM", "PRACTICALIST", "PRACTICALITY", "PRACTICALIZE", "PRAIRIECRAFT", 
    "PREPRACTICAL", "PRETEMPERATE", "PROSILVERITE", "QUENCHLESSLY", "QUICKSILVERY", "SCISSORSMITH", 
    "SEMIANNEALED", "SEMIMETALLIC", "SHOEINGSMITH", "SILVERBEATER", "SILVERWORKER", "SMITHYDANDER", 
    "SUBTEMPERATE", "SUPERENGRAVE", "TEMPEREDNESS", "THEOPHRASTAN", "THEOPHYLLINE", "THEOPHYSICAL", 
    "UNATTEMPERED", "UNCRAFTINESS", "UNFORGETTING", "UNQUENCHABLE", "UNQUENCHABLY", "WEAPONSMITHY", 
    "WOODMANCRAFT", "TRANSPOSITION", "CRYPTOGRAPHY", "CIPHERCLERKS", "SECRETWRITING"
};

int main() {
    load_quads();

    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int Z_std[N];
    for (int i=0; i<N; i++) {
        int c_k = k2i[(int)CT[i]];
        int z_k = (c_k - shifts[i % 28] + 26) % 26;
        Z_std[i] = ALPH[z_k] - 'A';
    }

    FILE *f = fopen("words_12.txt", "r");
    char (*all_words)[16] = malloc(25000 * sizeof(*all_words));
    int (*all_orders)[12] = malloc(25000 * sizeof(*all_orders));
    int n_all = 0;
    char buf[64];
    while (fgets(buf, sizeof(buf), f)) {
        int len = strlen(buf);
        while (len > 0 && (buf[len-1] == '\n' || buf[len-1] == '\r')) buf[--len] = 0;
        if (len == W) {
            for (int i=0; i<W; i++) if (buf[i]>='a' && buf[i]<='z') buf[i] -= 32;
            strcpy(all_words[n_all], buf);
            word_to_order(buf, W, all_orders[n_all]);
            n_all++;
        }
    }
    fclose(f);

    int n_them = sizeof(thematic_words) / sizeof(thematic_words[0]);
    int them_orders[n_them][12];
    for (int i=0; i<n_them; i++) {
        word_to_order(thematic_words[i], W, them_orders[i]);
    }

    printf("Testing all %d thematic words x %d dictionary words (both orientations)...\n", n_them, n_all);
    float global_best_sc = -1e9f;
    char global_best_w1[16], global_best_w2[16];
    char global_best_pt[N+1];

    #pragma omp parallel for schedule(dynamic, 1)
    for (int i = 0; i < n_them; i++) {
        for (int j = 0; j < n_all; j++) {
            // Orientation 1: o1 = thematic, o2 = dict
            int pt1[N];
            double_col_dec(Z_std, all_orders[j], them_orders[i], pt1);
            float sc1 = eval_pt(pt1);
            if (sc1 > -4.8f) {
                #pragma omp critical
                {
                    if (sc1 > global_best_sc) {
                        global_best_sc = sc1;
                        strcpy(global_best_w1, thematic_words[i]);
                        strcpy(global_best_w2, all_words[j]);
                        for (int k=0; k<N; k++) global_best_pt[k] = pt1[k] + 'A';
                        global_best_pt[N] = 0;
                        printf(">>> HIT (%.4f): w1=%s, w2=%s <<<\n  PT: %s\n", sc1, thematic_words[i], all_words[j], global_best_pt);
                    }
                }
            }

            // Orientation 2: o1 = dict, o2 = thematic
            int pt2[N];
            double_col_dec(Z_std, them_orders[i], all_orders[j], pt2);
            float sc2 = eval_pt(pt2);
            if (sc2 > -4.8f) {
                #pragma omp critical
                {
                    if (sc2 > global_best_sc) {
                        global_best_sc = sc2;
                        strcpy(global_best_w1, all_words[j]);
                        strcpy(global_best_w2, thematic_words[i]);
                        for (int k=0; k<N; k++) global_best_pt[k] = pt2[k] + 'A';
                        global_best_pt[N] = 0;
                        printf(">>> HIT (%.4f): w1=%s, w2=%s <<<\n  PT: %s\n", sc2, all_words[j], thematic_words[i], global_best_pt);
                    }
                }
            }
        }
    }

    printf("\nFinished sweep! Global best: %.4f (w1=%s, w2=%s)\nPT: %s\n",
           global_best_sc, global_best_w1, global_best_w2, global_best_pt);
    return 0;
}

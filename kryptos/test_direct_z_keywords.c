#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144
#define W 12
#define H 12

static const char *Z_chunks[12] = {
    "UTNMSAOFWSUE",
    "ISWDOSCTFAIH",
    "RMOTISEGELTA",
    "ERWUHEHTTRAH",
    "RLENFTMDRNOS",
    "TOMRSIANEENS",
    "ACONNRHIEELD",
    "HNSALNAOEIOS",
    "ISAUIFDNEFFO",
    "HDLERNCOPDSO",
    "IHSNSSACSISF",
    "OHOONWEEDHIU"
};

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

void invert_perm(const int *p, int len, int *inv) {
    for (int i = 0; i < len; i++) {
        inv[p[i]] = i;
    }
}

float eval_perm(const int *p) {
    float sc = 0;
    for (int r = 0; r < H; r++) {
        int row[W];
        for (int c = 0; c < W; c++) {
            row[c] = Z_chunks[r][p[c]] - 'A';
        }
        for (int c = 0; c < W - 3; c++) {
            sc += quadgrams[row[c]][row[c+1]][row[c+2]][row[c+3]];
        }
    }
    return sc / (H * (W - 3));
}

int main() {
    load_quads();

    FILE *f = fopen("words_12.txt", "r");
    char word[64];
    float best_sc = -1e9f;
    char best_word[64];
    int best_mode = 0;

    while (fgets(word, sizeof(word), f)) {
        int len = strlen(word);
        while (len > 0 && (word[len-1] == '\n' || word[len-1] == '\r')) word[--len] = 0;
        if (len != W) continue;
        for (int i=0; i<W; i++) if (word[i]>='a' && word[i]<='z') word[i] -= 32;

        int order[W], inv_order[W];
        word_to_order(word, W, order);
        invert_perm(order, W, inv_order);

        // Test normal order
        float sc1 = eval_perm(order);
        if (sc1 > best_sc) {
            best_sc = sc1;
            strcpy(best_word, word);
            best_mode = 1;
            printf("New best (order): %s -> Score: %.4f\n", best_word, best_sc);
        }

        // Test inverse order
        float sc2 = eval_perm(inv_order);
        if (sc2 > best_sc) {
            best_sc = sc2;
            strcpy(best_word, word);
            best_mode = 2;
            printf("New best (inv_order): %s -> Score: %.4f\n", best_word, best_sc);
        }
    }
    fclose(f);

    printf("\nGLOBAL BEST: %s (mode %d, Score: %.4f)\n", best_word, best_mode, best_sc);
    int p[W];
    if (best_mode == 1) word_to_order(best_word, W, p);
    else {
        int ord[W];
        word_to_order(best_word, W, ord);
        invert_perm(ord, W, p);
    }
    for (int r = 0; r < H; r++) {
        char row[W+1];
        for (int c = 0; c < W; c++) row[c] = Z_chunks[r][p[c]];
        row[W] = 0;
        printf("Row %2d: %s\n", r, row);
    }

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

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

    FILE *f = fopen("english_quadgrams.txt", "r");
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

void col_dec(const int *in, const int *order, int *out) {
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
    char word[64];
    float best_sc = -1e9f;
    char best_word[64];
    char best_pt[N+1];

    while (fgets(word, sizeof(word), f)) {
        int len = strlen(word);
        while (len > 0 && (word[len-1] == '\n' || word[len-1] == '\r')) word[--len] = 0;
        if (len != W) continue;
        for (int i=0; i<W; i++) if (word[i]>='a' && word[i]<='z') word[i] -= 32;

        int order[W];
        word_to_order(word, W, order);

        int pt[N];
        col_dec(Z_std, order, pt);

        float sc = 0;
        for (int i=0; i<N-3; i++) {
            sc += quadgrams[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
        }
        sc /= (N - 3);

        if (sc > best_sc) {
            best_sc = sc;
            strcpy(best_word, word);
            for (int i=0; i<N; i++) best_pt[i] = pt[i] + 'A';
            best_pt[N] = 0;
            printf("New best word: %s (score: %.4f)\n  PT: %s\n", best_word, best_sc, best_pt);
        }
    }
    fclose(f);

    printf("\nGLOBAL BEST KEYWORD: %s (Score: %.4f)\nPT: %s\n", best_word, best_sc, best_pt);
    return 0;
}

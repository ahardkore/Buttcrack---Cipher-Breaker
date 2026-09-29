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

// Invert single columnar
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

// Undo double columnar: P = col_dec(col_dec(Z, o2), o1)
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

int main(int argc, char **argv) {
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

    // Load words
    const char *wordfile = (argc > 1) ? argv[1] : "words_12.txt";
    FILE *f = fopen(wordfile, "r");
    if (!f) { printf("Failed to open %s\n", wordfile); return 1; }

    char (*words)[16] = malloc(30000 * sizeof(*words));
    int (*orders)[12] = malloc(30000 * sizeof(*orders));
    int n_words = 0;
    char buf[64];
    while (fgets(buf, sizeof(buf), f)) {
        int len = strlen(buf);
        while (len > 0 && (buf[len-1] == '\n' || buf[len-1] == '\r')) buf[--len] = 0;
        if (len == W) {
            for (int i=0; i<W; i++) {
                if (buf[i]>='a' && buf[i]<='z') buf[i] -= 32;
            }
            strcpy(words[n_words], buf);
            word_to_order(buf, W, orders[n_words]);
            n_words++;
            if (n_words >= 30000) break;
        }
    }
    fclose(f);
    printf("Loaded %d words of length %d from %s.\n", n_words, W, wordfile);

    int max_test = (n_words > 1000) ? 1000 : n_words;
    printf("Testing all %lld ordered pairs among top %d words...\n", (long long)max_test * max_test, max_test);

    float global_best_sc = -1e9f;
    char global_best_w1[16], global_best_w2[16];
    char global_best_pt[N+1];

    double t0 = omp_get_wtime();

    #pragma omp parallel for schedule(dynamic, 1)
    for (int i = 0; i < max_test; i++) {
        for (int j = 0; j < max_test; j++) {
            int pt[N];
            // Decrypt: Z -> undo o2 (words[j]) -> undo o1 (words[i]) -> P
            double_col_dec(Z_std, orders[j], orders[i], pt);
            float sc = eval_pt(pt);

            if (sc > -4.5f) {
                #pragma omp critical
                {
                    if (sc > global_best_sc) {
                        global_best_sc = sc;
                        strcpy(global_best_w1, words[i]);
                        strcpy(global_best_w2, words[j]);
                        for (int k=0; k<N; k++) global_best_pt[k] = pt[k] + 'A';
                        global_best_pt[N] = 0;
                        printf(">>> HIT! (%.4f) w1=%s, w2=%s <<<\n  PT: %s\n",
                               sc, words[i], words[j], global_best_pt);
                    }
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Evaluated %lld pairs in %.2f seconds (%.0f pairs/sec).\n",
           (long long)max_test * max_test, elapsed, (double)max_test * max_test / elapsed);
    if (global_best_sc > -1e8f) {
        printf("Global best: %.4f (w1=%s, w2=%s)\nPT: %s\n",
               global_best_sc, global_best_w1, global_best_w2, global_best_pt);
    } else {
        printf("No pair exceeded threshold -4.5.\n");
    }

    return 0;
}

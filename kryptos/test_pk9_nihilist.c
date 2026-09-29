#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define W 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static const int q7[7] = {0, 2, 9, 23, 23, 6, 20};

static float quadgrams[26][26][26][26];

void load_quads() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    quadgrams[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
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
    int used[12] = {0};
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

// Decode Nihilist grid
// takeoff: 0 = columns, 1 = rows
void decode_nihilist(const int *cipher_letters, const int *col_order, const int *row_order, int takeoff, int *plain) {
    int sq3[12][12];
    int k = 0;
    if (takeoff == 1) { // rows
        for (int r = 0; r < 12; r++)
            for (int c = 0; c < 12; c++)
                sq3[r][c] = cipher_letters[k++];
    } else { // columns
        for (int c = 0; c < 12; c++)
            for (int r = 0; r < 12; r++)
                sq3[r][c] = cipher_letters[k++];
    }

    int sq2[12][12];
    for (int i = 0; i < 12; i++) {
        int r_orig = row_order[i];
        for (int c = 0; c < 12; c++) {
            sq2[r_orig][c] = sq3[i][c];
        }
    }

    int grid[12][12];
    for (int r = 0; r < 12; r++) {
        for (int c = 0; c < 12; c++) {
            int c_orig = col_order[c];
            grid[r][c_orig] = sq2[r][c];
        }
    }

    k = 0;
    for (int r = 0; r < 12; r++)
        for (int c = 0; c < 12; c++)
            plain[k++] = grid[r][c];
}

int main() {
    load_quads();

    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int ct_k[N];
    for (int i=0; i<N; i++) ct_k[i] = k2i[(int)CT[i]];

    FILE *f = fopen("words_12.txt", "r");
    char (*words)[16] = malloc(25000 * sizeof(*words));
    int (*orders)[12] = malloc(25000 * sizeof(*orders));
    int n_words = 0;
    char buf[64];
    while (fgets(buf, sizeof(buf), f)) {
        if (buf[strlen(buf)-1] == '\n') buf[strlen(buf)-1] = 0;
        if (buf[strlen(buf)-1] == '\r') buf[strlen(buf)-1] = 0;
        if (strlen(buf) == 12) {
            for (int i=0; i<12; i++) if (buf[i]>='a'&&buf[i]<='z') buf[i]-=32;
            strcpy(words[n_words], buf);
            word_to_order(buf, 12, orders[n_words]);
            n_words++;
        }
    }
    fclose(f);
    printf("Loaded %d words for Nihilist Transposition.\n", n_words);

    float global_best = -1e9;
    char best_word[16];
    char best_pt[N+1];
    int best_parity = 0;
    int best_takeoff = 0;

    for (int parity = 0; parity < 16; parity++) {
        int q4_bits[4];
        for (int b=0; b<4; b++) q4_bits[b] = ((parity >> b) & 1) * 13;

        int Z_std[N];
        for (int i=0; i<N; i++) {
            int shift = (q7[i % 7] + q4_bits[i % 4]) % 26;
            int z_kr = (ct_k[i] - shift + 26) % 26;
            Z_std[i] = ALPH[z_kr] - 'A';
        }

        #pragma omp parallel for
        for (int w = 0; w < n_words; w++) {
            for (int takeoff = 0; takeoff < 2; takeoff++) {
                int pt[N];
                decode_nihilist(Z_std, orders[w], orders[w], takeoff, pt);

                float sc = 0;
                for (int i=0; i<N-3; i++) {
                    sc += quadgrams[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                }
                sc /= (N - 3);

                if (sc > -6.0f) {
                    #pragma omp critical
                    {
                        if (sc > global_best) {
                            global_best = sc;
                            strcpy(best_word, words[w]);
                            best_parity = parity;
                            best_takeoff = takeoff;
                            for (int i=0; i<N; i++) best_pt[i] = pt[i] + 'A';
                            best_pt[N] = 0;
                            printf("\nHIT! Score = %.4f | Word: %s | Parity %d | Takeoff %d\n",
                                   sc, words[w], parity, takeoff);
                            printf("PT: %s\n", best_pt);
                        }
                    }
                }
            }
        }
    }

    printf("Nihilist sweep completed across all 20,453 words, 16 parities, 2 takeoffs.\n");
    if (global_best > -1e8) {
        printf("Best: %.4f | Word: %s | Parity %d | Takeoff %d\nPT: %s\n",
               global_best, best_word, best_parity, best_takeoff, best_pt);
    } else {
        printf("No candidate exceeded -6.0/quadgram.\n");
    }

    return 0;
}

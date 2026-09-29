#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

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

// Myszkowski column numbering
void get_mysz_groups(const char *word, int len, int *n_groups, int group_sizes[32], int group_cols[32][32]) {
    // Find distinct letters in alphabetical order
    char distinct[32];
    int n_dist = 0;
    for (char c = 'A'; c <= 'Z'; c++) {
        for (int i = 0; i < len; i++) {
            if (word[i] == c) {
                distinct[n_dist++] = c;
                break;
            }
        }
    }

    *n_groups = n_dist;
    for (int g = 0; g < n_dist; g++) {
        char c = distinct[g];
        int count = 0;
        for (int i = 0; i < len; i++) {
            if (word[i] == c) {
                group_cols[g][count++] = i;
            }
        }
        group_sizes[g] = count;
    }
}

// Decode Myszkowski
void decode_myszkowski(const int *cipher_letters, int width, int n_groups, const int group_sizes[32], const int group_cols[32][32], int *plain) {
    int nrows = N / width;
    int grid[600][32];
    int idx = 0;

    for (int g = 0; g < n_groups; g++) {
        int sz = group_sizes[g];
        if (sz == 1) {
            int c = group_cols[g][0];
            for (int r = 0; r < nrows; r++) {
                grid[r][c] = cipher_letters[idx++];
            }
        } else {
            for (int r = 0; r < nrows; r++) {
                for (int i = 0; i < sz; i++) {
                    int c = group_cols[g][i];
                    grid[r][c] = cipher_letters[idx++];
                }
            }
        }
    }

    int pt_idx = 0;
    for (int r = 0; r < nrows; r++) {
        for (int c = 0; c < width; c++) {
            plain[pt_idx++] = grid[r][c];
        }
    }
}

void test_width_myszkowski(const char *fn, int width) {
    FILE *f = fopen(fn, "r");
    if (!f) return;

    char (*words)[32] = malloc(60000 * sizeof(*words));
    int n_words = 0;
    char buf[64];
    while (fgets(buf, sizeof(buf), f) && n_words < 60000) {
        if (buf[strlen(buf)-1] == '\n') buf[strlen(buf)-1] = 0;
        if (buf[strlen(buf)-1] == '\r') buf[strlen(buf)-1] = 0;
        if (strlen(buf) == width) {
            for (int i=0; i<width; i++) if (buf[i]>='a'&&buf[i]<='z') buf[i]-=32;
            strcpy(words[n_words++], buf);
        }
    }
    fclose(f);

    printf("Testing Myszkowski Width %2d (%d words from %s)...\n", width, n_words, fn);

    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int ct_k[N];
    for (int i=0; i<N; i++) ct_k[i] = k2i[(int)CT[i]];

    float best_sc = -1e9;
    char best_w[32] = "";
    int best_parity = 0;
    char best_pt[N+1];

    for (int parity = 0; parity < 16; parity++) {
        int q4_bits[4];
        for (int b=0; b<4; b++) q4_bits[b] = ((parity >> b) & 1) * 13;

        int Z_std[N];
        for (int i=0; i<N; i++) {
            int shift = (q7[i % 7] + q4_bits[i % 4]) % 26;
            int z_kr = (ct_k[i] - shift + 26) % 26;
            Z_std[i] = ALPH[z_kr] - 'A';
        }

        #pragma omp parallel for schedule(dynamic, 100)
        for (int w = 0; w < n_words; w++) {
            int n_groups;
            int group_sizes[32];
            int group_cols[32][32];
            get_mysz_groups(words[w], width, &n_groups, group_sizes, group_cols);

            // If all group sizes are 1, it's just regular columnar transposition which was already tested
            if (n_groups == width) continue;

            int plain[N];
            decode_myszkowski(Z_std, width, n_groups, group_sizes, group_cols, plain);

            float sc = 0;
            for (int i=0; i<N-3; i++) {
                sc += quadgrams[plain[i]][plain[i+1]][plain[i+2]][plain[i+3]];
            }
            sc /= (N - 3);

            if (sc > -6.0f) {
                #pragma omp critical
                {
                    if (sc > best_sc) {
                        best_sc = sc;
                        strcpy(best_w, words[w]);
                        best_parity = parity;
                        for (int i=0; i<N; i++) best_pt[i] = plain[i] + 'A';
                        best_pt[N] = 0;
                        printf("\nMysz HIT! Width %d | Score = %.4f | Word: %s | Parity %d\n",
                               width, sc, words[w], parity);
                        printf("PT: %s\n", best_pt);
                    }
                }
            }
        }
    }

    if (best_sc > -1e8) {
        printf("Width %d Best: %.4f | Word: %s (Parity %d)\n", width, best_sc, best_w, best_parity);
    } else {
        printf("Width %d: No Myszkowski candidate exceeded -6.0/quadgram.\n", width);
    }

    free(words);
}

int main() {
    load_quads();
    test_width_myszkowski("words_6.txt", 6);
    test_width_myszkowski("words_8.txt", 8);
    test_width_myszkowski("words_9.txt", 9);
    test_width_myszkowski("words_12.txt", 12);
    return 0;
}

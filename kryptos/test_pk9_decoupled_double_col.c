#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define W 12
#define H 12

// Kryptos alphabet
static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";

// PK9 raw ciphertext
static const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

// Universal q7
static const int q7[7] = {0, 2, 9, 23, 23, 6, 20};

// Quadgram table
static float qgram[26][26][26][26];

void load_quadgrams() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    qgram[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
    if (!f) {
        printf("Error: quadgrams file not found\n");
        exit(1);
    }
    char line[64];
    double total = 5348433.0;
    while (fgets(line, sizeof(line), f)) {
        char g[5];
        double count;
        if (sscanf(line, "%4s %lf", g, &count) == 2) {
            int a = g[0] - 'A';
            int b = g[1] - 'A';
            int c = g[2] - 'A';
            int d = g[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                qgram[a][b][c][d] = (float)log10(count / total);
            }
        }
    }
    fclose(f);
}

// Convert word to order (standard columnar order)
void word_to_order(const char *word, int len, int *order) {
    int used[ len ];
    memset(used, 0, sizeof(used));
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

// Invert permutation
void invert_perm(const int *p, int len, int *inv) {
    for (int i = 0; i < len; i++) {
        inv[p[i]] = i;
    }
}

int main() {
    load_quadgrams();

    // Map letters to indices
    int a2i[256];
    int k2i[256];
    for (int i=0; i<256; i++) { a2i[i] = -1; k2i[i] = -1; }
    for (int i=0; i<26; i++) {
        a2i['A' + i] = i;
        k2i[(int)ALPH[i]] = i;
    }

    int ct_k[N];
    for (int i=0; i<N; i++) ct_k[i] = k2i[(int)CT[i]];

    // Load words_12.txt
    FILE *f = fopen("words_12.txt", "r");
    if (!f) { printf("Failed to open words_12.txt\n"); return 1; }
    char (*words)[16] = malloc(25000 * sizeof(*words));
    int (*orders)[12] = malloc(25000 * sizeof(*orders));
    int (*inv_orders)[12] = malloc(25000 * sizeof(*inv_orders));
    int n_words = 0;
    char buf[64];
    while (fgets(buf, sizeof(buf), f)) {
        if (buf[strlen(buf)-1] == '\n') buf[strlen(buf)-1] = 0;
        if (buf[strlen(buf)-1] == '\r') buf[strlen(buf)-1] = 0;
        if (strlen(buf) == 12) {
            for (int i=0; i<12; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] -= 32;
            }
            strcpy(words[n_words], buf);
            word_to_order(buf, 12, orders[n_words]);
            invert_perm(orders[n_words], 12, inv_orders[n_words]);
            n_words++;
        }
    }
    fclose(f);
    printf("Loaded %d 12-letter words.\n", n_words);

    // Test both conventions:
    // Model A: c[12*m + r'] = P[12*o2[m] + o1[r']]
    // Model B: c[12*m + r'] = P[12*o1[m] + o2[r']] (the transposed convention)
    
    // There are 16 parity masks for q4: q4 in {0, 13}^4
    for (int parity = 0; parity < 16; parity++) {
        int q4_bits[4];
        for (int b=0; b<4; b++) q4_bits[b] = ((parity >> b) & 1) * 13;

        // Derive intermediate stream Z
        int Z[N];
        for (int i=0; i<N; i++) {
            int shift = (q7[i % 7] + q4_bits[i % 4]) % 26;
            Z[i] = (ct_k[i] - shift + 26) % 26;
        }

        // Convert Z to standard English alphabet indices
        int Z_std[N];
        for (int i=0; i<N; i++) {
            char ch = ALPH[Z[i]];
            Z_std[i] = ch - 'A';
        }

        float best_score = -1e9;
        int best_word_idx = -1;
        int best_model = -1;

        #pragma omp parallel for reduction(max:best_score)
        for (int w = 0; w < n_words; w++) {
            // Model A: Each chunk m of Z is permuted by inv_orders[w]
            // That is, row letters are Z_std[12*m + inv_orders[w][col]]
            float scoreA = 0;
            for (int m = 0; m < 12; m++) {
                int row[12];
                for (int col = 0; col < 12; col++) {
                    row[col] = Z_std[12*m + inv_orders[w][col]];
                }
                for (int col = 0; col <= 8; col++) {
                    scoreA += qgram[row[col]][row[col+1]][row[col+2]][row[col+3]];
                }
            }
            if (scoreA > best_score) {
                best_score = scoreA;
            }

            // Model B: Z is written in columns, or chunked differently
            // That is, chunk m corresponds to col m, row r corresponds to row
            float scoreB = 0;
            for (int r = 0; r < 12; r++) {
                int row[12];
                for (int col = 0; col < 12; col++) {
                    // Transposed: index is 12*inv_orders[w][col] + r
                    row[col] = Z_std[12*inv_orders[w][col] + r];
                }
                for (int col = 0; col <= 8; col++) {
                    scoreB += qgram[row[col]][row[col+1]][row[col+2]][row[col+3]];
                }
            }
            if (scoreB > best_score) {
                best_score = scoreB;
            }
        }

        // Find which word achieved best_score
        for (int w = 0; w < n_words; w++) {
            float scoreA = 0;
            for (int m = 0; m < 12; m++) {
                int row[12];
                for (int col = 0; col < 12; col++) row[col] = Z_std[12*m + inv_orders[w][col]];
                for (int col = 0; col <= 8; col++) scoreA += qgram[row[col]][row[col+1]][row[col+2]][row[col+3]];
            }
            float scoreB = 0;
            for (int r = 0; r < 12; r++) {
                int row[12];
                for (int col = 0; col < 12; col++) row[col] = Z_std[12*inv_orders[w][col] + r];
                for (int col = 0; col <= 8; col++) scoreB += qgram[row[col]][row[col+1]][row[col+2]][row[col+3]];
            }
            if (fabs(scoreA - best_score) < 1e-4) {
                best_word_idx = w;
                best_model = 1;
                break;
            }
            if (fabs(scoreB - best_score) < 1e-4) {
                best_word_idx = w;
                best_model = 2;
                break;
            }
        }

        printf("Parity %2d: Best Score = %8.2f (avg %6.3f/qg) | Model %d | Word = %s\n",
               parity, best_score, best_score / 108.0f, best_model, words[best_word_idx]);
    }

    return 0;
}

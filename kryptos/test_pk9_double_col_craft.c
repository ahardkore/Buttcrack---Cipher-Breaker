#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *Z_text = "KLBQKNSFKCANNSKPPXCSGLQJEMUWQNKIOPOAHTCPMELWYNAJYRJUVTBPSSQBXLNRCMNRIEVZOROUQENLUEAPNSUCEOBOHMLHNSDHGTDUFVLAXDATSSXAWVAOMLMRDSDYTASHSXDAPWRTIRTW";

static float quadgrams[26][26][26][26];

static void init_tables(void) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quadgrams[a][b][c][d] = -12.0f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Cannot open english_quadgrams.txt\n"); exit(1); }
    char line[64];
    long long total = 0;
    while (fgets(line, sizeof(line), f)) {
        char qg[5];
        long long count;
        if (sscanf(line, "%4s %lld", qg, &count) == 2) total += count;
    }
    fseek(f, 0, SEEK_SET);
    while (fgets(line, sizeof(line), f)) {
        char qg[5];
        long long count;
        if (sscanf(line, "%4s %lld", qg, &count) == 2) {
            int a = qg[0] - 'A', b = qg[1] - 'A', c = qg[2] - 'A', d = qg[3] - 'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26) {
                quadgrams[a][b][c][d] = log10f((float)count / total);
            }
        }
    }
    fclose(f);
}

// Complete columnar decryption
// In complete columnar: grid has H rows and W columns.
// Ciphertext is written down columns in key order.
// Plaintext is read out row by row.
void col_decrypt(const char *ct, const int *order, char *pt) {
    char grid[H][W];
    int idx = 0;
    for (int k = 0; k < W; k++) {
        int col = order[k];
        for (int r = 0; r < H; r++) {
            grid[r][col] = ct[idx++];
        }
    }
    idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            pt[idx++] = grid[r][c];
        }
    }
    pt[N] = '\0';
}

// Compute alphabetical column order from a keyword
void get_order(const char *word, int *order) {
    int len = strlen(word);
    int used[16] = {0};
    int k = 0;
    for (char ch = 'A'; ch <= 'Z'; ch++) {
        for (int i = 0; i < len; i++) {
            if (word[i] == ch && !used[i]) {
                order[k++] = i;
                used[i] = 1;
            }
        }
    }
}

typedef struct {
    float score;
    char w1[16];
    char w2[16];
    char pt[N + 1];
} Hit;

int main(void) {
    init_tables();

    // Load 12-letter words
    char words[1000][16];
    int n_words = 0;

    FILE *f1 = fopen("craft_words_12.txt", "r");
    while (fscanf(f1, "%15s", words[n_words]) == 1) {
        if (strlen(words[n_words]) == 12) n_words++;
    }
    fclose(f1);

    FILE *f2 = fopen("theophilus_english_12.txt", "r");
    while (fscanf(f2, "%15s", words[n_words]) == 1) {
        if (strlen(words[n_words]) == 12) n_words++;
    }
    fclose(f2);

    // Deduplicate
    int unique_n = 0;
    char uniq_words[1000][16];
    for (int i = 0; i < n_words; i++) {
        int found = 0;
        for (int j = 0; j < unique_n; j++) {
            if (strcmp(words[i], uniq_words[j]) == 0) { found = 1; break; }
        }
        if (!found) strcpy(uniq_words[unique_n++], words[i]);
    }

    printf("Loaded %d unique 12-letter words -> %lld pairs\n",
        unique_n, (long long)unique_n * unique_n);

    int orders[1000][W];
    for (int i = 0; i < unique_n; i++) {
        get_order(uniq_words[i], orders[i]);
    }

    Hit top[20];
    for (int i = 0; i < 20; i++) top[i].score = -1e9f;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        Hit local_top[20];
        for (int i = 0; i < 20; i++) local_top[i].score = -1e9f;

        #pragma omp for schedule(dynamic, 10)
        for (int i1 = 0; i1 < unique_n; i1++) {
            int *o1 = orders[i1];
            for (int i2 = 0; i2 < unique_n; i2++) {
                int *o2 = orders[i2];

                // Two-stage columnar decryption:
                // C -> col_decrypt(o2) -> Z1 -> col_decrypt(o1) -> P
                char z1[N + 1];
                char pt[N + 1];
                col_decrypt(Z_text, o2, z1);
                col_decrypt(z1, o1, pt);

                float sc = 0;
                for (int t = 0; t < N - 3; t++) {
                    int a = pt[t] - 'A';
                    int b = pt[t+1] - 'A';
                    int c = pt[t+2] - 'A';
                    int d = pt[t+3] - 'A';
                    sc += quadgrams[a][b][c][d];
                }
                float avg_sc = sc / (N - 3);

                if (avg_sc > local_top[19].score) {
                    int pos = 19;
                    while (pos > 0 && avg_sc > local_top[pos - 1].score) {
                        local_top[pos] = local_top[pos - 1];
                        pos--;
                    }
                    local_top[pos].score = avg_sc;
                    strcpy(local_top[pos].w1, uniq_words[i1]);
                    strcpy(local_top[pos].w2, uniq_words[i2]);
                    strcpy(local_top[pos].pt, pt);
                }
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < 20; i++) {
                float s = local_top[i].score;
                if (s > top[19].score) {
                    int pos = 19;
                    while (pos > 0 && s > top[pos - 1].score) {
                        top[pos] = top[pos - 1];
                        pos--;
                    }
                    top[pos] = local_top[i];
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("Completed sweep in %.3f seconds!\n\n", t1 - t0);

    printf("Top 10 Decryptions of PK9 under Double Columnar:\n");
    for (int i = 0; i < 10; i++) {
        printf("#%2d: Score = %5.2f | (%s, %s)\n",
            i + 1, top[i].score, top[i].w1, top[i].w2);
        printf("    PT: %s\n", top[i].pt);
    }

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include <time.h>

#define N 504

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int ct_kr[N];

void init_ct() {
    FILE *f = fopen("pk_all_ciphertexts.json", "r");
    if (!f) { printf("Cannot open json\n"); exit(1); }
    char buf[4096];
    size_t len = fread(buf, 1, sizeof(buf) - 1, f);
    buf[len] = '\0';
    fclose(f);

    char *p = strstr(buf, "\"PK10\": \"");
    p += 9;
    int hpos[256];
    for (int i = 0; i < 26; i++) hpos[(unsigned char)KRYPTOS[i]] = i;
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)p[i]];
}

// Compute slice IoC for period p
static inline float slice_ioc(const int *stream, int p) {
    int total_num = 0;
    int total_den = 0;
    for (int rem = 0; rem < p; rem++) {
        int counts[26] = {0};
        int n_sub = 0;
        for (int i = rem; i < N; i += p) {
            counts[stream[i]]++;
            n_sub++;
        }
        if (n_sub > 1) {
            int num = 0;
            for (int k = 0; k < 26; k++) num += counts[k] * (counts[k] - 1);
            total_num += num;
            total_den += n_sub * (n_sub - 1);
        }
    }
    return (total_den > 0) ? (float)total_num / (float)total_den : 0.0f;
}

// Derive column read order from word (stable sort)
void word_to_order(const char *word, int len, int *order) {
    for (int i = 0; i < len; i++) order[i] = i;
    for (int i = 0; i < len - 1; i++) {
        for (int j = i + 1; j < len; j++) {
            if (word[order[j]] < word[order[i]]) {
                int tmp = order[i];
                order[i] = order[j];
                order[j] = tmp;
            }
        }
    }
}

// Undo columnar transposition
// In columnar transposition: text is written into matrix of width W by rows, then read out by columns in 'order'.
// To undo: we fill columns in 'order' with the ciphertext, then read out by rows.
void undo_columnar(const int *ct, int W, int H, const int *order, int *out) {
    int cols[W][H];
    int idx = 0;
    for (int c = 0; c < W; c++) {
        int col_idx = order[c];
        for (int r = 0; r < H; r++) {
            cols[col_idx][r] = ct[idx++];
        }
    }
    idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            out[idx++] = cols[c][r];
        }
    }
}

// Also test the inverse convention: write by columns, read by rows in 'order'
void undo_columnar_alt(const int *ct, int W, int H, const int *order, int *out) {
    int rows[H][W];
    int idx = 0;
    for (int r = 0; r < H; r++) {
        int row_idx = order[r % W]; // if H == W
        for (int c = 0; c < W; c++) {
            rows[r][c] = ct[idx++];
        }
    }
    // Read by columns
    idx = 0;
    for (int c = 0; c < W; c++) {
        for (int r = 0; r < H; r++) {
            out[idx++] = rows[r][c];
        }
    }
}

typedef struct {
    char word[32];
    int len;
} Word;

int main() {
    init_ct();

    // Load words
    FILE *f = fopen("all_words.txt", "r");
    if (!f) { printf("Cannot open all_words.txt\n"); exit(1); }

    int cap = 150000;
    Word *words = malloc(cap * sizeof(Word));
    int n_words = 0;

    char buf[128];
    while (fscanf(f, "%127s", buf) == 1) {
        int l = strlen(buf);
        if (l == 7 || l == 8 || l == 9 || l == 12 || l == 14) {
            int valid = 1;
            for (int i = 0; i < l; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] -= 32;
                if (buf[i] < 'A' || buf[i] > 'Z') { valid = 0; break; }
            }
            if (valid) {
                if (n_words >= cap) { cap *= 2; words = realloc(words, cap * sizeof(Word)); }
                strcpy(words[n_words].word, buf);
                words[n_words].len = l;
                n_words++;
            }
        }
    }
    fclose(f);
    printf("Loaded %d candidate transposition keywords from all_words.txt\n", n_words);

    double t0 = omp_get_wtime();
    float best_total_ioc = 0.0f;
    char best_word[32] = "";
    int best_W = 0;

    #pragma omp parallel
    {
        float loc_best_ioc = 0.0f;
        char loc_best_word[32] = "";
        int loc_best_W = 0;

        #pragma omp for schedule(dynamic, 100)
        for (int i = 0; i < n_words; i++) {
            int W = words[i].len;
            int H = N / W;
            int order[32];
            word_to_order(words[i].word, W, order);

            int undone[N];
            undo_columnar(ct_kr, W, H, order, undone);

            float i7 = slice_ioc(undone, 7);
            float i8 = slice_ioc(undone, 8);
            float i9 = slice_ioc(undone, 9);
            float tot_ioc = i7 + i8 + i9;

            if (tot_ioc > 0.160f || i7 > 0.060f || i8 > 0.060f || i9 > 0.060f) {
                #pragma omp critical
                {
                    printf(">>> SPIKE HIT! Word: %s (W=%d) | IoC(7)=%.4f, IoC(8)=%.4f, IoC(9)=%.4f | Tot=%.4f <<<\n",
                           words[i].word, W, i7, i8, i9, tot_ioc);
                }
            }

            if (tot_ioc > loc_best_ioc) {
                loc_best_ioc = tot_ioc;
                strcpy(loc_best_word, words[i].word);
                loc_best_W = W;
            }
        }

        #pragma omp critical
        {
            if (loc_best_ioc > best_total_ioc) {
                best_total_ioc = loc_best_ioc;
                strcpy(best_word, loc_best_word);
                best_W = loc_best_W;
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nSweep of %d keywords finished in %.3f seconds!\n", n_words, elapsed);
    printf("Best Keyword: %s (W=%d) | Total IoC = %.4f (Avg = %.4f)\n",
           best_word, best_W, best_total_ioc, best_total_ioc / 3.0f);

    free(words);
    return 0;
}

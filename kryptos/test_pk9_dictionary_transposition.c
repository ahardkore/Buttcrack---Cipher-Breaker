#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) return;
    char q[16]; float cnt;
    double total = 0;
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    rewind(f);
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int k_to_std[26];
static int std_to_k[26];

// The Period-28 shifts from earlier
static const int shifts28[28] = {
    5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 7, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3
};

static char z_28[N + 1];

void init() {
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        std_to_k[KRYPTOS[i] - 'A'] = i;
    }
    for (int i=0; i<N; i++) {
        ct_kr[i] = std_to_k[PK9_REAL[i] - 'A'];
        int p_kr = (ct_kr[i] - shifts28[i % 28] + 26) % 26;
        z_28[i] = k_to_std[p_kr] + 'A';
    }
    z_28[N] = '\0';
}

float score_text(const char *t) {
    float sc = 0.0f;
    for (int i=0; i<N-3; i++) {
        sc += quad[t[i]-'A'][t[i+1]-'A'][t[i+2]-'A'][t[i+3]-'A'];
    }
    return sc / (N - 3);
}

void get_word_order(const char *w, int len, int *order) {
    for (int i=0; i<len; i++) order[i] = i;
    for (int i=0; i<len-1; i++) {
        for (int j=i+1; j<len; j++) {
            if (w[order[i]] > w[order[j]]) {
                int tmp = order[i]; order[i] = order[j]; order[j] = tmp;
            }
        }
    }
}

void test_single_col_dict(const char *fn, int width) {
    FILE *f = fopen(fn, "r");
    if (!f) return;
    
    char word[64];
    int height = N / width;
    
    float best_sc = -999.0f;
    char best_word[64] = "";
    char best_pt[N+1];
    int count = 0;
    
    char pt[N+1];
    pt[N] = '\0';
    int order[64];
    
    while (fscanf(f, "%63s", word) == 1) {
        if (strlen(word) != width) continue;
        count++;
        get_word_order(word, width, order);
        
        // Decrypt columnar:
        // Ciphertext z_28 was read out column by column in order 'order'.
        // So column c received z_28[c*height : (c+1)*height].
        // In the grid, row r, col order[c] has z_28[c*height + r].
        // Reading row by row: pt[r*width + order[c]] = z_28[c*height + r].
        for (int c = 0; c < width; c++) {
            int col_orig = order[c];
            for (int r = 0; r < height; r++) {
                pt[r * width + col_orig] = z_28[c * height + r];
            }
        }
        
        float sc = score_text(pt);
        if (sc > best_sc) {
            best_sc = sc;
            strcpy(best_word, word);
            strcpy(best_pt, pt);
            if (sc > -5.2f) {
                printf("\n*** SINGLE COL HIT! File: %s | Width: %d | Word: %s | Quad: %.3f ***\n",
                       fn, width, word, sc);
                printf("PT: %s\n", pt);
            }
        }
        
        // Also test the inverse convention:
        // pt[r*width + c] = z_28[order[c]*height + r]
        for (int c = 0; c < width; c++) {
            int col_src = order[c];
            for (int r = 0; r < height; r++) {
                pt[r * width + c] = z_28[col_src * height + r];
            }
        }
        sc = score_text(pt);
        if (sc > best_sc) {
            best_sc = sc;
            strcpy(best_word, word);
            strcpy(best_pt, pt);
            if (sc > -5.2f) {
                printf("\n*** SINGLE COL HIT (Inv)! File: %s | Width: %d | Word: %s | Quad: %.3f ***\n",
                       fn, width, word, sc);
                printf("PT: %s\n", pt);
            }
        }
    }
    fclose(f);
    printf("Width %2d | File: %-25s | Tested: %6d | Best: %-15s | Quad: %.3f\n",
           width, fn, count, best_word, best_sc);
    if (best_sc > -6.0f) {
        printf("  PT: %.80s...\n", best_pt);
    }
}

int main() {
    load_quads();
    init();
    printf("Models initialized. z_28 prepared (len %d).\n\n", (int)strlen(z_28));
    
    // Test single columnar transpositions across all divisor widths
    test_single_col_dict("words_6.txt", 6);
    test_single_col_dict("theophilus_w6.txt", 6);
    test_single_col_dict("words_8.txt", 8);
    test_single_col_dict("theophilus_w8.txt", 8);
    test_single_col_dict("words_9.txt", 9);
    test_single_col_dict("theophilus_w9.txt", 9);
    test_single_col_dict("words_12.txt", 12);
    test_single_col_dict("theophilus_w12_all.txt", 12);
    test_single_col_dict("words_16.txt", 16);
    test_single_col_dict("words_18.txt", 18);
    return 0;
}

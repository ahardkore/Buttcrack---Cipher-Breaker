#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int c_idx[N];

void init_tables() {
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
    }
}

// Compute coset IoC of integer array at period P
float compute_coset_ioc(const int *text, int len, int P) {
    float total_ioc = 0.0f;
    int slices = 0;
    for (int r = 0; r < P; r++) {
        int counts[26] = {0};
        int cnt = 0;
        for (int i = r; i < len; i += P) {
            counts[text[i]]++;
            cnt++;
        }
        if (cnt >= 2) {
            int sum_sq = 0;
            for (int c = 0; c < 26; c++) {
                sum_sq += counts[c] * (counts[c] - 1);
            }
            total_ioc += (float)sum_sq / (float)(cnt * (cnt - 1));
            slices++;
        }
    }
    return slices > 0 ? (total_ioc / slices) : 0.0f;
}

// Single columnar decode
void single_col_decode(const int *in, int len, int width, const int *order, int *out) {
    int h = len / width;
    int grid[150][30];
    int k = 0;
    for (int m = 0; m < width; m++) {
        int col = order[m];
        for (int r = 0; r < h; r++) {
            grid[r][col] = in[k++];
        }
    }
    int idx = 0;
    for (int r = 0; r < h; r++) {
        for (int c = 0; c < width; c++) {
            out[idx++] = grid[r][c];
        }
    }
}

void word_to_order(const char *w, int len, int *order) {
    typedef struct { char ch; int orig; } Pair;
    Pair p[32];
    for (int i = 0; i < len; i++) { p[i].ch = w[i]; p[i].orig = i; }
    for (int i = 0; i < len - 1; i++) {
        for (int j = i + 1; j < len; j++) {
            if (p[j].ch < p[i].ch || (p[j].ch == p[i].ch && p[j].orig < p[i].orig)) {
                Pair tmp = p[i]; p[i] = p[j]; p[j] = tmp;
            }
        }
    }
    for (int i = 0; i < len; i++) order[i] = p[i].orig;
}

int main() {
    init_tables();

    printf("=== Baseline Raw PK9 Coset IoC ===\n");
    for (int p = 2; p <= 30; p++) {
        float ioc = compute_coset_ioc(c_idx, N, p);
        if (ioc > 0.050f) {
            printf("  Period %2d: Coset IoC = %.5f\n", p, ioc);
        }
    }

    // Test dictionary words for widths 6, 8, 9, 12
    const char *files[4] = {"curated_w6.txt", "words_8.txt", "words_9.txt", "words_12.txt"};
    int widths[4] = {6, 8, 9, 12};

    for (int f_idx = 0; f_idx < 4; f_idx++) {
        int w = widths[f_idx];
        FILE *f = fopen(files[f_idx], "r");
        if (!f) {
            printf("Could not open %s\n", files[f_idx]);
            continue;
        }

        char line[64];
        int count = 0;
        float best_ioc_p7 = 0.0f;
        char best_word_p7[32] = "";
        float best_ioc_p12 = 0.0f;
        char best_word_p12[32] = "";

        while (fgets(line, sizeof(line), f)) {
            char word[32];
            if (sscanf(line, "%s", word) == 1 && strlen(word) == w) {
                int order[32];
                word_to_order(word, w, order);

                int Y[N];
                single_col_decode(c_idx, N, w, order, Y);

                float ioc7 = compute_coset_ioc(Y, N, 7);
                if (ioc7 > best_ioc_p7) {
                    best_ioc_p7 = ioc7;
                    strcpy(best_word_p7, word);
                }

                float ioc12 = compute_coset_ioc(Y, N, 12);
                if (ioc12 > best_ioc_p12) {
                    best_ioc_p12 = ioc12;
                    strcpy(best_word_p12, word);
                }
                count++;
            }
        }
        fclose(f);

        printf("\nWidth %2d (%s, %d words):\n", w, files[f_idx], count);
        printf("  Best Period  7 Coset IoC: %.5f (Word: %s)\n", best_ioc_p7, best_word_p7);
        printf("  Best Period 12 Coset IoC: %.5f (Word: %s)\n", best_ioc_p12, best_word_p12);
    }

    return 0;
}

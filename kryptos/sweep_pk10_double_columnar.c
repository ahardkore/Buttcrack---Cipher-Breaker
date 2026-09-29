#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504

const char *PK10_CT = "WKVZSVZMWZMVBVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZVKVTVYVXVTVQVZ";

// Real PK10 ciphertext will be loaded from JSON
static char real_ct10[N + 1];

void load_real_ct10() {
    FILE *f = fopen("pk_all_ciphertexts.json", "r");
    if (!f) { printf("Cannot open pk_all_ciphertexts.json\n"); exit(1); }
    char buf[4096];
    int found = 0;
    while (fgets(buf, sizeof(buf), f)) {
        if (strstr(buf, "\"PK10\"")) {
            char *p = strchr(buf, ':');
            if (p) {
                p = strchr(p, '\"');
                if (p) {
                    p++;
                    char *end = strchr(p, '\"');
                    if (end) {
                        *end = '\0';
                        strcpy(real_ct10, p);
                        found = 1;
                        break;
                    }
                }
            }
        }
    }
    fclose(f);
    if (!found || strlen(real_ct10) != N) {
        printf("Failed to load real PK10 (len=%zu)\n", strlen(real_ct10));
        exit(1);
    }
    printf("Loaded real PK10: len=%zu, first 30: %.30s\n", strlen(real_ct10), real_ct10);
}

typedef struct {
    char str[16];
    int order[16];
    int len;
} Keyword;

static Keyword *words7 = NULL; static int n7 = 0;
static Keyword *words8 = NULL; static int n8 = 0;
static Keyword *words9 = NULL; static int n9 = 0;

void load_keywords_for_len(int target_len, Keyword **kw_arr, int *n_arr, int max_count) {
    FILE *f = fopen("all_words.txt", "r");
    if (!f) { printf("Cannot open all_words.txt\n"); exit(1); }
    *kw_arr = malloc(max_count * sizeof(Keyword));
    *n_arr = 0;
    char buf[128];
    while (fscanf(f, "%127s", buf) == 1 && *n_arr < max_count) {
        if (strlen(buf) == target_len) {
            int valid = 1;
            for (int i = 0; i < target_len; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] -= 32;
                if (buf[i] < 'A' || buf[i] > 'Z') { valid = 0; break; }
            }
            if (!valid) continue;

            Keyword *kw = &(*kw_arr)[*n_arr];
            strcpy(kw->str, buf);
            kw->len = target_len;

            // Compute standard columnar read order
            int idx[16];
            for (int i = 0; i < target_len; i++) idx[i] = i;
            for (int i = 0; i < target_len - 1; i++) {
                for (int j = i + 1; j < target_len; j++) {
                    if (buf[idx[j]] < buf[idx[i]] || (buf[idx[j]] == buf[idx[i]] && idx[j] < idx[i])) {
                        int tmp = idx[i]; idx[i] = idx[j]; idx[j] = tmp;
                    }
                }
            }
            for (int i = 0; i < target_len; i++) kw->order[i] = idx[i];
            (*n_arr)++;
        }
    }
    fclose(f);
    printf("Loaded %d words of length %d.\n", *n_arr, target_len);
}

// Invert regular columnar transposition
static inline void undo_columnar(const char *in, char *out, const int *order, int W) {
    int H = N / W;
    // in has W columns of length H, ordered by order[0], order[1], ...
    // Column c = order[k] starts at in + k * H
    char grid[504]; // flattened grid [r * W + c]
    for (int k = 0; k < W; k++) {
        int c = order[k];
        const char *col_src = in + k * H;
        for (int r = 0; r < H; r++) {
            grid[r * W + c] = col_src[r];
        }
    }
    memcpy(out, grid, N);
    out[N] = '\0';
}

// Fast slice IoC
static inline double calc_slice_ioc(const char *s, int p) {
    double sum_ioc = 0.0;
    int m = N / p;
    for (int r = 0; r < p; r++) {
        int cnt[26] = {0};
        for (int i = r; i < N; i += p) {
            cnt[s[i] - 'A']++;
        }
        int pairs = 0;
        for (int c = 0; c < 26; c++) pairs += cnt[c] * (cnt[c] - 1);
        sum_ioc += (double)pairs / (m * (m - 1));
    }
    return sum_ioc / p;
}

int main() {
    load_real_ct10();

    load_keywords_for_len(7, &words7, &n7, 3000);
    load_keywords_for_len(8, &words8, &n8, 3000);
    load_keywords_for_len(9, &words9, &n9, 3000);

    // Baseline IoC
    printf("\nBaseline IoC on raw PK10: p7=%.4f, p8=%.4f, p9=%.4f\n\n",
           calc_slice_ioc(real_ct10, 7), calc_slice_ioc(real_ct10, 8), calc_slice_ioc(real_ct10, 9));

    // Test pairs: (W9, W9), (W8, W8), (W7, W7), (W8, W9), (W7, W8)
    struct {
        Keyword *kw1; int n1; int w1;
        Keyword *kw2; int n2; int w2;
        const char *name;
    } configs[] = {
        {words9, n9, 9, words9, n9, 9, "Double Width 9 (like PK6)"},
        {words8, n8, 8, words8, n8, 8, "Double Width 8"},
        {words7, n7, 7, words7, n7, 7, "Double Width 7"},
        {words8, n8, 8, words9, n9, 9, "Width 8 then Width 9"},
        {words7, n7, 7, words8, n8, 8, "Width 7 then Width 8"},
        {words7, n7, 7, words9, n9, 9, "Width 7 then Width 9"}
    };

    for (int cfg = 0; cfg < 6; cfg++) {
        printf("====================================================\n");
        printf("Testing Configuration: %s (%d x %d = %ld pairs)\n",
               configs[cfg].name, configs[cfg].n1, configs[cfg].n2,
               (long)configs[cfg].n1 * configs[cfg].n2);
        printf("====================================================\n");

        double t0 = omp_get_wtime();
        double best_ioc = 0.0;
        char best_w1[16] = "", best_w2[16] = "";
        int best_p = 0;

        #pragma omp parallel
        {
            double loc_best_ioc = 0.0;
            char loc_w1[16] = "", loc_w2[16] = "";
            int loc_p = 0;

            #pragma omp for schedule(dynamic, 16)
            for (int i1 = 0; i1 < configs[cfg].n1; i1++) {
                char s1[N + 1];
                undo_columnar(real_ct10, s1, configs[cfg].kw1[i1].order, configs[cfg].w1);

                for (int i2 = 0; i2 < configs[cfg].n2; i2++) {
                    char s2[N + 1];
                    undo_columnar(s1, s2, configs[cfg].kw2[i2].order, configs[cfg].w2);

                    for (int p = 7; p <= 9; p++) {
                        double ioc = calc_slice_ioc(s2, p);
                        if (ioc > 0.055) {
                            #pragma omp critical
                            {
                                printf(">>> BREAKTHROUGH SPIKE! IoC(%d) = %.5f <<<\n", p, ioc);
                                printf("  Stage 1: %s (W=%d), Stage 2: %s (W=%d)\n\n",
                                       configs[cfg].kw1[i1].str, configs[cfg].w1,
                                       configs[cfg].kw2[i2].str, configs[cfg].w2);
                            }
                        }
                        if (ioc > loc_best_ioc) {
                            loc_best_ioc = ioc;
                            loc_p = p;
                            strcpy(loc_w1, configs[cfg].kw1[i1].str);
                            strcpy(loc_w2, configs[cfg].kw2[i2].str);
                        }
                    }
                }
            }

            #pragma omp critical
            {
                if (loc_best_ioc > best_ioc) {
                    best_ioc = loc_best_ioc;
                    best_p = loc_p;
                    strcpy(best_w1, loc_w1);
                    strcpy(best_w2, loc_w2);
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        printf("Swept in %.3f s | Best IoC = %.5f (Period %d) with words: %s + %s\n\n",
               elapsed, best_ioc, best_p, best_w1, best_w2);
    }

    free(words7); free(words8); free(words9);
    return 0;
}

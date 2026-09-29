#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const float eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015,
    0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749,
    0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758,
    0.00978, 0.02360, 0.00150, 0.01974, 0.00074
};

static int c_idx[N];
static int alpha_to_std[26];
static int char_to_k[256];

void init_tables() {
    for (int i = 0; i < 256; i++) char_to_k[i] = -1;
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
        char_to_k[(unsigned char)KRYPTOS[i]] = i;
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = char_to_k[(unsigned char)PK9_CT[i]];
    }
}

typedef struct {
    char word[16];
    int idx[12];
} Word12;

typedef struct {
    char word[8];
    int idx[7];
} Word7;

static Word12 *words12 = NULL;
static int n12 = 0;
static Word7 *words7 = NULL;
static int n7 = 0;

void load_words() {
    FILE *f12 = fopen("words_12.txt", "r");
    char buf[64];
    words12 = malloc(25000 * sizeof(Word12));
    while (fgets(buf, sizeof(buf), f12)) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 12) {
            int valid = 1;
            for (int i = 0; i < 12; i++) {
                int k = char_to_k[(unsigned char)buf[i]];
                if (k < 0) { valid = 0; break; }
                words12[n12].idx[i] = k;
            }
            if (valid) {
                strcpy(words12[n12].word, buf);
                n12++;
            }
        }
    }
    fclose(f12);

    FILE *f7 = fopen("words_7.txt", "r");
    words7 = malloc(50000 * sizeof(Word7));
    while (fgets(buf, sizeof(buf), f7)) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 7) {
            int valid = 1;
            for (int i = 0; i < 7; i++) {
                int k = char_to_k[(unsigned char)buf[i]];
                if (k < 0) { valid = 0; break; }
                words7[n7].idx[i] = k;
            }
            if (valid) {
                strcpy(words7[n7].word, buf);
                n7++;
            }
        }
    }
    fclose(f7);
    printf("Loaded %d 12-letter words and %d 7-letter words\n", n12, n7);
}

typedef struct {
    float dot;
    char w12[16];
    char w7[8];
} TopResult;

#define MAX_TOP 25
TopResult top_results[MAX_TOP];

void update_top(float dot, const char *w12, const char *w7) {
    if (dot <= top_results[MAX_TOP - 1].dot) return;
    int pos = MAX_TOP - 1;
    while (pos > 0 && dot > top_results[pos - 1].dot) {
        top_results[pos] = top_results[pos - 1];
        pos--;
    }
    top_results[pos].dot = dot;
    strcpy(top_results[pos].w12, w12);
    strcpy(top_results[pos].w7, w7);
}

int main() {
    init_tables();
    load_words();

    for (int i = 0; i < MAX_TOP; i++) top_results[i].dot = 0.0f;

    long long total_pairs = (long long)n12 * n7;
    printf("Evaluating all %lld pairs of (W12, W7) on PK9...\n", total_pairs);

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        TopResult local_top[MAX_TOP];
        for (int i = 0; i < MAX_TOP; i++) local_top[i].dot = 0.0f;

        #pragma omp for schedule(dynamic, 64)
        for (int i12 = 0; i12 < n12; i12++) {
            const Word12 *pw12 = &words12[i12];
            float slice_table[7][26];

            for (int j = 0; j < 7; j++) {
                for (int v = 0; v < 26; v++) {
                    float d = 0.0f;
                    for (int i = j; i < N; i += 7) {
                        int k = (pw12->idx[i % 12] + v) % 26;
                        int p = (c_idx[i] - k + 26) % 26;
                        d += eng_freq[alpha_to_std[p]];
                    }
                    slice_table[j][v] = d;
                }
            }

            for (int i7 = 0; i7 < n7; i7++) {
                const Word7 *pw7 = &words7[i7];
                float dot = slice_table[0][pw7->idx[0]] +
                            slice_table[1][pw7->idx[1]] +
                            slice_table[2][pw7->idx[2]] +
                            slice_table[3][pw7->idx[3]] +
                            slice_table[4][pw7->idx[4]] +
                            slice_table[5][pw7->idx[5]] +
                            slice_table[6][pw7->idx[6]];

                if (dot > local_top[MAX_TOP - 1].dot) {
                    int pos = MAX_TOP - 1;
                    while (pos > 0 && dot > local_top[pos - 1].dot) {
                        local_top[pos] = local_top[pos - 1];
                        pos--;
                    }
                    local_top[pos].dot = dot;
                    strcpy(local_top[pos].w12, pw12->word);
                    strcpy(local_top[pos].w7, pw7->word);
                }
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < MAX_TOP; i++) {
                if (local_top[i].dot > 0.0f) {
                    update_top(local_top[i].dot, local_top[i].w12, local_top[i].w7);
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f s (%.1f million pairs/sec)\n", elapsed, total_pairs / (elapsed * 1e6));

    printf("\nTop %d (W12, W7) Word Pairs by Monogram Dot Product:\n", MAX_TOP);
    for (int i = 0; i < MAX_TOP; i++) {
        printf("%2d. Dot = %.4f | W12 = %-14s | W7 = %-7s\n",
               i + 1, top_results[i].dot, top_results[i].w12, top_results[i].w7);
    }

    return 0;
}

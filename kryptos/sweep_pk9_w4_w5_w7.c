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
    char word[6];
    int idx[4];
} Word4;

typedef struct {
    char word[7];
    int idx[5];
} Word5;

typedef struct {
    char word[9];
    int idx[7];
} Word7;

static Word4 words4[1000];
static int n4 = 0;
static Word5 words5[1000];
static int n5 = 0;
static Word7 words7[50000];
static int n7 = 0;

void load_words() {
    FILE *f4 = fopen("theophilus_w4.txt", "r");
    char buf[64];
    while (fgets(buf, sizeof(buf), f4)) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 4) {
            int valid = 1;
            for (int i = 0; i < 4; i++) {
                int k = char_to_k[(unsigned char)buf[i]];
                if (k < 0) { valid = 0; break; }
                words4[n4].idx[i] = k;
            }
            if (valid) {
                strcpy(words4[n4].word, buf);
                n4++;
            }
        }
    }
    fclose(f4);

    FILE *f5 = fopen("theophilus_w5.txt", "r");
    while (fgets(buf, sizeof(buf), f5)) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 5) {
            int valid = 1;
            for (int i = 0; i < 5; i++) {
                int k = char_to_k[(unsigned char)buf[i]];
                if (k < 0) { valid = 0; break; }
                words5[n5].idx[i] = k;
            }
            if (valid) {
                strcpy(words5[n5].word, buf);
                n5++;
            }
        }
    }
    fclose(f5);

    FILE *f7 = fopen("words_7.txt", "r");
    while (fgets(buf, sizeof(buf), f7) && n7 < 50000) {
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
    printf("Loaded: %d w4, %d w5, %d w7\n", n4, n5, n7);
}

typedef struct {
    float dot;
    char w4[6];
    char w5[7];
    char w7[9];
} TopResult;

#define MAX_TOP 25
TopResult top_results[MAX_TOP];

void update_top(float dot, const char *w4, const char *w5, const char *w7) {
    if (dot <= top_results[MAX_TOP - 1].dot) return;
    int pos = MAX_TOP - 1;
    while (pos > 0 && dot > top_results[pos - 1].dot) {
        top_results[pos] = top_results[pos - 1];
        pos--;
    }
    top_results[pos].dot = dot;
    strcpy(top_results[pos].w4, w4);
    strcpy(top_results[pos].w5, w5);
    strcpy(top_results[pos].w7, w7);
}

int main() {
    init_tables();
    load_words();

    for (int i = 0; i < MAX_TOP; i++) top_results[i].dot = 0.0f;

    long long total_triples = (long long)n4 * n5 * n7;
    printf("Evaluating all %lld triples of (W4, W5, W7) on PK9...\n", total_triples);

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        TopResult local_top[MAX_TOP];
        for (int i = 0; i < MAX_TOP; i++) local_top[i].dot = 0.0f;

        #pragma omp for schedule(dynamic, 16)
        for (int i4 = 0; i4 < n4; i4++) {
            const Word4 *pw4 = &words4[i4];

            for (int i5 = 0; i5 < n5; i5++) {
                const Word5 *pw5 = &words5[i5];

                // Precompute K20
                int k20[20];
                for (int i = 0; i < 20; i++) {
                    k20[i] = (pw4->idx[i % 4] + pw5->idx[i % 5]) % 26;
                }

                // Build slice table for this (W4, W5) pair
                float slice_table[7][26];
                for (int j = 0; j < 7; j++) {
                    for (int v = 0; v < 26; v++) {
                        float d = 0.0f;
                        for (int i = j; i < N; i += 7) {
                            int k = (k20[i % 20] + v) % 26;
                            int p = (c_idx[i] - k + 26) % 26;
                            d += eng_freq[alpha_to_std[p]];
                        }
                        slice_table[j][v] = d;
                    }
                }

                // Inner sweep over all W7 words
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
                        strcpy(local_top[pos].w4, pw4->word);
                        strcpy(local_top[pos].w5, pw5->word);
                        strcpy(local_top[pos].w7, pw7->word);
                    }
                }
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < MAX_TOP; i++) {
                if (local_top[i].dot > 0.0f) {
                    update_top(local_top[i].dot, local_top[i].w4, local_top[i].w5, local_top[i].w7);
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f s (%.1f million triples/sec)\n", elapsed, total_triples / (elapsed * 1e6));

    printf("\nTop %d (W4, W5, W7) Triples by Monogram Dot Product:\n", MAX_TOP);
    for (int i = 0; i < MAX_TOP; i++) {
        printf("%2d. Dot = %.4f | (%s, %s, %s)\n",
               i + 1, top_results[i].dot, top_results[i].w4, top_results[i].w5, top_results[i].w7);
    }

    return 0;
}

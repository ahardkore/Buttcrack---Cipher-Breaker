#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 153

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const int q4[4] = {16, 23, 22, 18};
static const int q7[7] = {10, 19, 17, 25, 16, 18, 10};

static const int q2_5[5] = {0, 0, 1, 0, 0};
static const int q2_6[6] = {0, 0, 0, 1, 0, 0};

static int c_idx[N];
static int alpha_to_std[26];
static int char_to_k[256];
static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) exit(1);
    char q[16]; float sc;
    while (fscanf(f, "%s %f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

void init_tables() {
    for (int i = 0; i < 256; i++) char_to_k[i] = -1;
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
        char_to_k[(unsigned char)KRYPTOS[i]] = i;
    }
    for (int i = 0; i < N; i++) c_idx[i] = char_to_k[(unsigned char)PK8_CT[i]];
}

typedef struct { char word[8]; int idx[6]; } WordItem;

static WordItem list5[20000]; static int n5 = 0;
static WordItem list6[35000]; static int n6 = 0;

void load_words() {
    FILE *f; char buf[64];
    f = fopen("words_5.txt", "r");
    while (fgets(buf, sizeof(buf), f) && n5 < 20000) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 5) {
            int valid = 1;
            for (int i = 0; i < 5; i++) {
                int k = char_to_k[(unsigned char)buf[i]];
                if (k < 0) { valid = 0; break; }
                list5[n5].idx[i] = k;
            }
            if (valid) {
                strcpy(list5[n5].word, buf);
                n5++;
            }
        }
    }
    fclose(f);

    f = fopen("words_6.txt", "r");
    while (fgets(buf, sizeof(buf), f) && n6 < 35000) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 6) {
            int valid = 1;
            for (int i = 0; i < 6; i++) {
                int k = char_to_k[(unsigned char)buf[i]];
                if (k < 0) { valid = 0; break; }
                list6[n6].idx[i] = k;
            }
            if (valid) {
                strcpy(list6[n6].word, buf);
                n6++;
            }
        }
    }
    fclose(f);
    printf("Loaded %d 5-letter words and %d 6-letter words\n", n5, n6);
}

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    init_tables();
    load_quadgrams();
    load_words();

    printf("Sweeping English words (W5, W6) under PK9 bridge (Q4, Q7) on PK8...\n");

    // Filter words matching parity (with all rotations)
    float best_sc = -999.0f;
    char best_w5[8] = "", best_w6[8] = "";
    char best_pt[N + 1] = "";

    int pt[N];

    for (int i5 = 0; i5 < n5; i5++) {
        const WordItem *pw5 = &list5[i5];

        for (int i6 = 0; i6 < n6; i6++) {
            const WordItem *pw6 = &list6[i6];

            // Test base parity alignment
            int match5 = 1, match6 = 1;
            for (int k = 0; k < 5; k++) if (pw5->idx[k] % 2 != q2_5[k]) { match5 = 0; break; }
            if (!match5) continue;
            for (int k = 0; k < 6; k++) if (pw6->idx[k] % 2 != q2_6[k]) { match6 = 0; break; }
            if (!match6) continue;

            for (int i = 0; i < N; i++) {
                int shift = (q4[i % 4] + pw5->idx[i % 5] + pw6->idx[i % 6] + q7[i % 7]) % 26;
                int p = (c_idx[i] - shift + 26) % 26;
                pt[i] = alpha_to_std[p];
            }

            float sc = score_plain(pt);
            if (sc > best_sc) {
                best_sc = sc;
                strcpy(best_w5, pw5->word);
                strcpy(best_w6, pw6->word);
                for (int i = 0; i < N; i++) best_pt[i] = 'A' + pt[i];
                best_pt[N] = '\0';
                printf(">>> Hit! Score = %.4f | Words: (%s, %s)\n  PT: %.100s...\n",
                       sc, pw5->word, pw6->word, best_pt);
            }
        }
    }

    printf("\nBest Score = %.4f | Words: (%s, %s)\n", best_sc, best_w5, best_w6);
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
    char q[16]; float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *UNDONE = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

static int ct_kr[N];
static int ct_std[N];
static int k2std[26];
static int hpos[256];

typedef struct {
    char str[10];
    int kr[7];
    int std[7];
} Word7;

static Word7 *w7 = NULL;
static int n7 = 0;

void load_w7() {
    FILE *f = fopen("all_words.txt", "r");
    if (!f) { printf("Cannot open all_words.txt\n"); exit(1); }

    int cap = 40000;
    w7 = malloc(cap * sizeof(Word7));

    char buf[128];
    while (fscanf(f, "%127s", buf) == 1) {
        int l = strlen(buf);
        if (l == 7) {
            int valid = 1;
            for (int i = 0; i < 7; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] -= 32;
                if (buf[i] < 'A' || buf[i] > 'Z') { valid = 0; break; }
            }
            if (valid) {
                strcpy(w7[n7].str, buf);
                for (int i = 0; i < 7; i++) {
                    w7[n7].std[i] = buf[i] - 'A';
                    w7[n7].kr[i] = hpos[(unsigned char)buf[i]];
                }
                n7++;
            }
        }
    }
    fclose(f);
    printf("Loaded %d 7-letter words.\n", n7);
}

static inline float score_pt(const int *pt_std) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return s / (N - 3);
}

int main() {
    load_quads();

    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)UNDONE[i]];
        ct_std[i] = UNDONE[i] - 'A';
    }

    load_w7();

    const char *cipher_names[6] = {
        "Quagmire III (KRYPTOS)",
        "Standard Vigenere (A-Z)",
        "Variant Beaufort (KRYPTOS)",
        "Variant Beaufort (A-Z)",
        "Beaufort (KRYPTOS)",
        "Beaufort (A-Z)"
    };

    printf("Starting sweep of all 23,723 7-letter words on undone across 6 cipher models...\n\n");

    for (int c_type = 0; c_type < 6; c_type++) {
        printf("--- Testing %s ---\n", cipher_names[c_type]);

        float best_sc = -999.0f;
        char best_word[10] = "";
        char best_pt[N + 1] = "";

        #pragma omp parallel
        {
            float loc_best = -999.0f;
            char loc_word[10] = "";
            char loc_pt[N + 1] = "";

            #pragma omp for schedule(dynamic, 100)
            for (int w = 0; w < n7; w++) {
                int pt[N];
                for (int t = 0; t < N; t++) {
                    int k_kr = w7[w].kr[t % 7];
                    int k_std = w7[w].std[t % 7];

                    if (c_type == 0) { // Q3
                        int p = (ct_kr[t] - k_kr + 26) % 26;
                        pt[t] = k2std[p];
                    } else if (c_type == 1) { // Vig
                        pt[t] = (ct_std[t] - k_std + 26) % 26;
                    } else if (c_type == 2) { // Var Beaufort KR: P = (C + K) % 26
                        int p = (ct_kr[t] + k_kr) % 26;
                        pt[t] = k2std[p];
                    } else if (c_type == 3) { // Var Beaufort std
                        pt[t] = (ct_std[t] + k_std) % 26;
                    } else if (c_type == 4) { // Beaufort KR: P = (K - C) % 26
                        int p = (k_kr - ct_kr[t] + 26) % 26;
                        pt[t] = k2std[p];
                    } else if (c_type == 5) { // Beaufort std
                        pt[t] = (k_std - ct_std[t] + 26) % 26;
                    }
                }

                float sc = score_pt(pt);
                if (sc > -5.2f) {
                    #pragma omp critical
                    {
                        char pt_str[N + 1];
                        for (int t = 0; t < N; t++) pt_str[t] = 'A' + pt[t];
                        pt_str[N] = '\0';
                        printf(">>> BREAKTHROUGH! Score: %.4f | Word: %s <<<\n", sc, w7[w].str);
                        printf("  PT: %s\n\n", pt_str);
                    }
                }

                if (sc > loc_best) {
                    loc_best = sc;
                    strcpy(loc_word, w7[w].str);
                    for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                    loc_pt[N] = '\0';
                }
            }

            #pragma omp critical
            {
                if (loc_best > best_sc) {
                    best_sc = loc_best;
                    strcpy(best_word, loc_word);
                    strcpy(best_pt, loc_pt);
                }
            }
        }

        printf("Best Score: %.4f | Word: %s\n", best_sc, best_word);
        printf("PT: %.70s...\n\n", best_pt);
    }

    free(w7);
    return 0;
}

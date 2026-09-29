#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *M_STR = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";
static int M[144];
static const int N = 144;

typedef struct {
    char word[8];
    int shifts[7];
} Word;

static Word *w3_list = NULL;
static int n3 = 0;
static Word *w4_list = NULL;
static int n4 = 0;
static Word *w7_list = NULL;
static int n7 = 0;

void init() {
    for (int i = 0; i < 26; i++) {
        for (int j = 0; j < 26; j++) {
            for (int k = 0; k < 26; k++) {
                for (int l = 0; l < 26; l++) {
                    quad_table[i][j][k][l] = -9.0f;
                }
            }
        }
    }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { fprintf(stderr, "Cannot open quads\n"); exit(1); }
    char q[16];
    float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int c0 = q[0]-'A', c1 = q[1]-'A', c2 = q[2]-'A', c3 = q[3]-'A';
            if (c0>=0&&c0<26&&c1>=0&&c1<26&&c2>=0&&c2<26&&c3>=0&&c3<26) {
                quad_table[c0][c1][c2][c3] = sc;
            }
        }
    }
    fclose(f);

    for (int i = 0; i < 26; i++) {
        int std = ALPH_K[i] - 'A';
        k_to_std[i] = std;
        std_to_k[std] = i;
    }
    for (int i = 0; i < N; i++) {
        M[i] = std_to_k[M_STR[i] - 'A'];
    }

    // Load words
    w3_list = malloc(5000 * sizeof(Word));
    w4_list = malloc(10000 * sizeof(Word));
    w7_list = malloc(50000 * sizeof(Word));

    f = fopen("words_alpha.txt", "r");
    if (!f) { fprintf(stderr, "Cannot open words_alpha.txt\n"); exit(1); }
    char buf[64];
    while (fscanf(f, "%63s", buf) == 1) {
        int len = strlen(buf);
        if (len == 3) {
            int ok = 1;
            for (int i = 0; i < 3; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(w3_list[n3].word, buf);
            for (int i = 0; i < 3; i++) w3_list[n3].shifts[i] = std_to_k[buf[i] - 'A'];
            n3++;
        } else if (len == 4) {
            int ok = 1;
            for (int i = 0; i < 4; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(w4_list[n4].word, buf);
            for (int i = 0; i < 4; i++) w4_list[n4].shifts[i] = std_to_k[buf[i] - 'A'];
            n4++;
        } else if (len == 7) {
            int ok = 1;
            for (int i = 0; i < 7; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(w7_list[n7].word, buf);
            for (int i = 0; i < 7; i++) w7_list[n7].shifts[i] = std_to_k[buf[i] - 'A'];
            n7++;
        }
    }
    fclose(f);
    printf("Loaded: W3=%d, W4=%d, W7=%d\n", n3, n4, n7);
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    init();

    // 1. Test (W3, W7) on M across Quagmire III
    printf("--- Testing (W3, W7) on M (Quagmire III: P = M - W3 - W7) ---\n");
    float best_sc = -999.0f;
    char best_hit[64] = "";
    char best_pt[150] = "";

    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_hit[64] = "";
        char local_pt[150] = "";

        #pragma omp for schedule(dynamic, 100)
        for (int i7 = 0; i7 < n7; i7++) {
            const int *s7 = w7_list[i7].shifts;
            for (int i3 = 0; i3 < n3; i3++) {
                const int *s3 = w3_list[i3].shifts;

                // Quick gate: first 16 letters
                int pt[16];
                for (int i = 0; i < 16; i++) {
                    int k = (s3[i % 3] + s7[i % 7]) % 26;
                    int p_idx = (M[i] - k + 26) % 26;
                    pt[i] = k_to_std[p_idx];
                }
                float sc = 0.0f;
                for (int i = 0; i < 13; i++) sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                sc /= 13.0f;
                if (sc < -5.6f) continue;

                // Full 144
                int full_pt[144];
                for (int i = 0; i < 144; i++) {
                    int k = (s3[i % 3] + s7[i % 7]) % 26;
                    int p_idx = (M[i] - k + 26) % 26;
                    full_pt[i] = k_to_std[p_idx];
                }
                float full_sc = 0.0f;
                for (int i = 0; i < 141; i++) full_sc += quad_table[full_pt[i]][full_pt[i+1]][full_pt[i+2]][full_pt[i+3]];
                full_sc /= 141.0f;

                if (full_sc > local_best) {
                    local_best = full_sc;
                    sprintf(local_hit, "%s + %s", w3_list[i3].word, w7_list[i7].word);
                    for (int i = 0; i < 144; i++) local_pt[i] = full_pt[i] + 'A';
                    local_pt[144] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (local_best > best_sc) {
                best_sc = local_best;
                strcpy(best_hit, local_hit);
                strcpy(best_pt, local_pt);
                printf("New best (W3, W7): sc=%.3f | %s | PT: %.50s...\n", best_sc, best_hit, best_pt);
            }
        }
    }

    printf("Best (W3, W7) on M: score=%.3f (%s)\nPT: %s\n\n", best_sc, best_hit, best_pt);

    // 2. Test (W4, W7) on M across Quagmire III
    printf("--- Testing (W4, W7) on M (Quagmire III: P = M - W4 - W7) ---\n");
    best_sc = -999.0f;

    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_hit[64] = "";
        char local_pt[150] = "";

        #pragma omp for schedule(dynamic, 100)
        for (int i7 = 0; i7 < n7; i7++) {
            const int *s7 = w7_list[i7].shifts;
            for (int i4 = 0; i4 < n4; i4++) {
                const int *s4 = w4_list[i4].shifts;

                // Quick gate: first 16 letters
                int pt[16];
                for (int i = 0; i < 16; i++) {
                    int k = (s4[i & 3] + s7[i % 7]) % 26;
                    int p_idx = (M[i] - k + 26) % 26;
                    pt[i] = k_to_std[p_idx];
                }
                float sc = 0.0f;
                for (int i = 0; i < 13; i++) sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                sc /= 13.0f;
                if (sc < -5.6f) continue;

                // Full 144
                int full_pt[144];
                for (int i = 0; i < 144; i++) {
                    int k = (s4[i & 3] + s7[i % 7]) % 26;
                    int p_idx = (M[i] - k + 26) % 26;
                    full_pt[i] = k_to_std[p_idx];
                }
                float full_sc = 0.0f;
                for (int i = 0; i < 141; i++) full_sc += quad_table[full_pt[i]][full_pt[i+1]][full_pt[i+2]][full_pt[i+3]];
                full_sc /= 141.0f;

                if (full_sc > local_best) {
                    local_best = full_sc;
                    sprintf(local_hit, "%s + %s", w4_list[i4].word, w7_list[i7].word);
                    for (int i = 0; i < 144; i++) local_pt[i] = full_pt[i] + 'A';
                    local_pt[144] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (local_best > best_sc) {
                best_sc = local_best;
                strcpy(best_hit, local_hit);
                strcpy(best_pt, local_pt);
                printf("New best (W4, W7): sc=%.3f | %s | PT: %.50s...\n", best_sc, best_hit, best_pt);
            }
        }
    }

    printf("Best (W4, W7) on M: score=%.3f (%s)\nPT: %s\n", best_sc, best_hit, best_pt);
    return 0;
}

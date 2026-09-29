#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *M_STR = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";
static int M[144];
static const int N = 144;

typedef struct {
    char word[16];
    int shifts[14];
} Word14;

static Word14 *w14_list = NULL;
static int n14 = 0;

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

    w14_list = malloc(20000 * sizeof(Word14));
    f = fopen("words_alpha.txt", "r");
    if (!f) { fprintf(stderr, "Cannot open words_alpha.txt\n"); exit(1); }
    char buf[64];
    while (fscanf(f, "%63s", buf) == 1) {
        if (strlen(buf) == 14) {
            int ok = 1;
            for (int i = 0; i < 14; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(w14_list[n14].word, buf);
            for (int i = 0; i < 14; i++) w14_list[n14].shifts[i] = std_to_k[buf[i] - 'A'];
            n14++;
        }
    }
    fclose(f);
    printf("Loaded: W14=%d\n", n14);
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    init();

    printf("Testing all %d 14-letter words on M across Q3, Beaufort, and Variant Beaufort...\n", n14);

    float best_q3 = -999.0f, best_bf = -999.0f, best_vb = -999.0f;
    char best_w_q3[16] = "", best_w_bf[16] = "", best_w_vb[16] = "";
    char best_pt_q3[150] = "", best_pt_bf[150] = "", best_pt_vb[150] = "";

    for (int idx = 0; idx < n14; idx++) {
        const int *s14 = w14_list[idx].shifts;

        // 1. Quagmire III: P = (M - s14) mod 26
        int pt_q3[144];
        for (int i = 0; i < N; i++) {
            int p_idx = (M[i] - s14[i % 14] + 26) % 26;
            pt_q3[i] = k_to_std[p_idx];
        }
        float sc = 0.0f;
        for (int i = 0; i < N - 3; i++) sc += quad_table[pt_q3[i]][pt_q3[i+1]][pt_q3[i+2]][pt_q3[i+3]];
        sc /= (N - 3);
        if (sc > best_q3) {
            best_q3 = sc;
            strcpy(best_w_q3, w14_list[idx].word);
            for (int i = 0; i < N; i++) best_pt_q3[i] = pt_q3[i] + 'A';
            best_pt_q3[N] = '\0';
            if (sc > -5.5f) printf("HIT Q3: %s sc=%.3f | PT: %.50s...\n", w14_list[idx].word, sc, best_pt_q3);
        }

        // 2. Beaufort: P = (s14 - M) mod 26
        int pt_bf[144];
        for (int i = 0; i < N; i++) {
            int p_idx = (s14[i % 14] - M[i] + 26) % 26;
            pt_bf[i] = k_to_std[p_idx];
        }
        sc = 0.0f;
        for (int i = 0; i < N - 3; i++) sc += quad_table[pt_bf[i]][pt_bf[i+1]][pt_bf[i+2]][pt_bf[i+3]];
        sc /= (N - 3);
        if (sc > best_bf) {
            best_bf = sc;
            strcpy(best_w_bf, w14_list[idx].word);
            for (int i = 0; i < N; i++) best_pt_bf[i] = pt_bf[i] + 'A';
            best_pt_bf[N] = '\0';
            if (sc > -5.5f) printf("HIT BF: %s sc=%.3f | PT: %.50s...\n", w14_list[idx].word, sc, best_pt_bf);
        }

        // 3. Variant Beaufort: P = (M + s14) mod 26
        int pt_vb[144];
        for (int i = 0; i < N; i++) {
            int p_idx = (M[i] + s14[i % 14]) % 26;
            pt_vb[i] = k_to_std[p_idx];
        }
        sc = 0.0f;
        for (int i = 0; i < N - 3; i++) sc += quad_table[pt_vb[i]][pt_vb[i+1]][pt_vb[i+2]][pt_vb[i+3]];
        sc /= (N - 3);
        if (sc > best_vb) {
            best_vb = sc;
            strcpy(best_w_vb, w14_list[idx].word);
            for (int i = 0; i < N; i++) best_pt_vb[i] = pt_vb[i] + 'A';
            best_pt_vb[N] = '\0';
            if (sc > -5.5f) printf("HIT VB: %s sc=%.3f | PT: %.50s...\n", w14_list[idx].word, sc, best_pt_vb);
        }
    }

    printf("\nFinished testing all 14-letter words on M.\n");
    printf("Best Q3: sc=%.3f with %s\nPT: %s\n", best_q3, best_w_q3, best_pt_q3);
    printf("Best BF: sc=%.3f with %s\nPT: %s\n", best_bf, best_w_bf, best_pt_bf);
    printf("Best VB: sc=%.3f with %s\nPT: %s\n", best_vb, best_w_vb, best_pt_vb);

    return 0;
}

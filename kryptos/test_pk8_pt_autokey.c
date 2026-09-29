#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *ALPH_S = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char *CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static float quad_table[26][26][26][26];

void load_quads() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Cannot open quadgram file!\n"); exit(1); }
    char q[16]; float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26)
                quad_table[a][b][c][d] = sc;
        }
    }
    fclose(f);
}

int main() {
    load_quads();

    // Test PT autokey with curated words as primer
    FILE *f = fopen("curated_w6.txt", "r");
    char words[1000][16]; int nw = 0;
    while (fgets(words[nw], sizeof(words[nw]), f)) {
        words[nw][strcspn(words[nw], "\r\n")] = 0;
        if (strlen(words[nw]) == 6) nw++;
    }
    fclose(f);

    printf("Testing PT autokey with %d 6-letter primers...\n", nw);

    for (int model = 0; model < 2; model++) {
        const char *alph = model ? ALPH_S : ALPH_K;
        const char *mname = model ? "STANDARD" : "KRYPTOS";
        int c_idx[N];
        for (int i = 0; i < N; i++) c_idx[i] = strchr(alph, CT[i]) - alph;

        for (int w = 0; w < nw; w++) {
            int p_idx[N];
            int L = strlen(words[w]);
            for (int i = 0; i < L; i++) p_idx[i] = strchr(alph, words[w][i]) - alph;

            for (int i = L; i < N; i++) {
                p_idx[i] = (c_idx[i] - p_idx[i - L] + 26) % 26;
            }

            char pt[N+1];
            for (int i = 0; i < N; i++) pt[i] = alph[p_idx[i]];
            pt[N] = 0;

            float sc = 0.0f;
            for (int i = 0; i < N - 3; i++) {
                int a = pt[i]-'A', b = pt[i+1]-'A', c = pt[i+2]-'A', d = pt[i+3]-'A';
                if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26)
                    sc += quad_table[a][b][c][d];
                else sc += -9.5f;
            }
            sc /= (N - 3);

            if (sc > -6.5f) {
                printf("[PT Autokey %s Primer=%s] sc=%.3f | PT: %.50s...\n", mname, words[w], sc, pt);
            }
        }
    }
    printf("PT Autokey test complete.\n");
    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

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

float score_text(const char *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        int a = pt[i]-'A', b = pt[i+1]-'A', c = pt[i+2]-'A', d = pt[i+3]-'A';
        if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26)
            s += quad_table[a][b][c][d];
        else s += -9.5f;
    }
    return s / (N - 3);
}

int main() {
    load_quads();

    // 1. Ciphertext Autokey test (key is previous ciphertext letter)
    // C_i = P_i + C_{i-L}
    for (int model = 0; model < 2; model++) {
        const char *alph = model ? ALPH_S : ALPH_K;
        const char *mname = model ? "STANDARD" : "KRYPTOS";
        int c_idx[N];
        for (int i = 0; i < N; i++) c_idx[i] = strchr(alph, CT[i]) - alph;

        for (int L = 1; L <= 20; L++) {
            // For CT autokey, each pos i >= L has key c_idx[i - L]!
            // We just need to check the score of the decrypted text from L onwards!
            char pt[N+1];
            for (int i = 0; i < L; i++) pt[i] = 'E'; // placeholder
            for (int i = L; i < N; i++) {
                int p_idx = (c_idx[i] - c_idx[i - L] + 26) % 26;
                pt[i] = alph[p_idx];
            }
            pt[N] = 0;
            float sc = score_text(pt);
            if (sc > -7.0f) {
                printf("[CT Autokey %s L=%d] sc=%.3f | PT: %.50s...\n", mname, L, sc, pt + L);
            }
        }
    }

    printf("Tested CT autokey across lengths 1..20.\n");
    return 0;
}

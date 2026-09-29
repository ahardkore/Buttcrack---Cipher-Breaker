#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *M = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

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
    if (!f) {
        fprintf(stderr, "Cannot open english_quads.tsv\n");
        exit(1);
    }
    char q[16];
    float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int c0 = q[0] - 'A', c1 = q[1] - 'A', c2 = q[2] - 'A', c3 = q[3] - 'A';
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
}

int main() {
    init();
    int N = strlen(M);
    int C[144];
    for (int i = 0; i < N; i++) {
        C[i] = std_to_k[M[i] - 'A'];
    }

    // Step 1: For each (s0, s1, s2, s3), score the quadgrams at 7k, 7k+1, 7k+2, 7k+3
    // There are 21 such positions (k = 0..20)
    printf("Evaluating 26^4 = 456,976 prefixes (s0, s1, s2, s3)...\n");

    // We can also just test all 26^7 directly or branch and bound!
    // Since 26^7 = 8e9, let's do a top-K beam search or branch-and-bound:
    // For s0, s1, s2, s3: find top 5000 combinations.
    typedef struct {
        float score;
        int s[4];
    } Cand4;

    Cand4 *cands = (Cand4 *)malloc(456976 * sizeof(Cand4));
    int count = 0;

    for (int s0 = 0; s0 < 26; s0++) {
        for (int s1 = 0; s1 < 26; s1++) {
            for (int s2 = 0; s2 < 26; s2++) {
                for (int s3 = 0; s3 < 26; s3++) {
                    float total = 0.0f;
                    for (int k = 0; k < 21; k++) {
                        int i = 7 * k;
                        int p0 = k_to_std[(C[i] - s0 + 26) % 26];
                        int p1 = k_to_std[(C[i+1] - s1 + 26) % 26];
                        int p2 = k_to_std[(C[i+2] - s2 + 26) % 26];
                        int p3 = k_to_std[(C[i+3] - s3 + 26) % 26];
                        total += quad_table[p0][p1][p2][p3];
                    }
                    cands[count].score = total / 21.0f;
                    cands[count].s[0] = s0;
                    cands[count].s[1] = s1;
                    cands[count].s[2] = s2;
                    cands[count].s[3] = s3;
                    count++;
                }
            }
        }
    }

    // Find the best prefix scores
    float best_prefix = -999.0f;
    for (int i = 0; i < count; i++) {
        if (cands[i].score > best_prefix) best_prefix = cands[i].score;
    }
    printf("Best 4-prefix average quadgram score: %.3f\n", best_prefix);

    // Print top 10 prefixes
    // Quick select / partial sort
    for (int iter = 0; iter < 10; iter++) {
        int best_idx = -1;
        float cur_max = -999.0f;
        for (int i = 0; i < count; i++) {
            if (cands[i].score > cur_max) {
                cur_max = cands[i].score;
                best_idx = i;
            }
        }
        if (best_idx >= 0) {
            printf("Rank %d: score=%.3f | key=(%c,%c,%c,%c) = shifts(%d,%d,%d,%d)\n",
                   iter+1, cands[best_idx].score,
                   ALPH_K[cands[best_idx].s[0]], ALPH_K[cands[best_idx].s[1]],
                   ALPH_K[cands[best_idx].s[2]], ALPH_K[cands[best_idx].s[3]],
                   cands[best_idx].s[0], cands[best_idx].s[1],
                   cands[best_idx].s[2], cands[best_idx].s[3]);
            cands[best_idx].score = -9999.0f; // eliminate
        }
    }

    return 0;
}

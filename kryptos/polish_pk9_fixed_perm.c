#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

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
static int k2std[26];
static int hpos[256];

static inline float eval_fixed_perm(const int *shifts, const int *perm, int *out_pt) {
    int p1[N];
    for (int t = 0; t < N; t++) {
        int s = shifts[t % 14];
        int p_kr = (ct_kr[t] - s + 26) % 26;
        p1[t] = k2std[p_kr];
    }

    int pt[N];
    int idx = 0;
    for (int r = 0; r < 12; r++) {
        for (int c = 0; c < 12; c++) {
            pt[idx++] = p1[r * 12 + perm[c]];
        }
    }

    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
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
    }

    int perm[12] = {9, 3, 6, 11, 10, 7, 8, 5, 1, 2, 4, 0};
    const char *init_key_str = "BYAACYUOHGODBU";
    int shifts[14];
    for (int i = 0; i < 14; i++) shifts[i] = hpos[(unsigned char)init_key_str[i]];

    float cur_sc = eval_fixed_perm(shifts, perm, NULL);
    printf("Initial Score: %.4f | Key: %s\n", cur_sc, init_key_str);

    // Iterative coordinate descent on 14 shifts
    int improved = 1;
    int round = 0;
    while (improved) {
        improved = 0;
        round++;
        for (int pos = 0; pos < 14; pos++) {
            int old_v = shifts[pos];
            int best_v = old_v;
            float best_delta = 0.0f;

            for (int diff = 1; diff < 26; diff++) {
                shifts[pos] = (old_v + diff) % 26;
                float sc = eval_fixed_perm(shifts, perm, NULL);
                if (sc - cur_sc > best_delta) {
                    best_delta = sc - cur_sc;
                    best_v = shifts[pos];
                }
            }

            if (best_delta > 1e-4f) {
                shifts[pos] = best_v;
                cur_sc += best_delta;
                improved = 1;
            } else {
                shifts[pos] = old_v;
            }
        }
        printf("Round %d: Score = %.4f | Key: ", round, cur_sc);
        for (int i = 0; i < 14; i++) printf("%c", KRYPTOS[shifts[i]]);
        printf("\n");
    }

    int pt[N];
    eval_fixed_perm(shifts, perm, pt);
    char pt_str[N + 1];
    for (int i = 0; i < N; i++) pt_str[i] = 'A' + pt[i];
    pt_str[N] = '\0';

    printf("\nPolished Plaintext:\n%s\n\n", pt_str);
    printf("Formatted in 12-char rows:\n");
    for (int r = 0; r < 12; r++) {
        char buf[13];
        memcpy(buf, pt_str + r * 12, 12);
        buf[12] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}

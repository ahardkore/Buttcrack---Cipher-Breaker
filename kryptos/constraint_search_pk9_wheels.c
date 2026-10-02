/* constraint_search_pk9_wheels.c — dictionary search for PK9's (q5, q6) wheel
 * pair under the tq model (T8 first, then Q(5)+Q(6)+Q(7)), using exact
 * algebraic constraints derived from PK9's structural ciphertext repeats.
 *
 * Under tq: C[i] = M[i] + q5[i%5] + q6[i%6] + q7[i%7], M = T8(P).
 * For any lag multiple of 7 the q7 part cancels, so a ciphertext repeat
 * C[i] == C[i+7k] with underlying plaintext repeat forces
 *      t[(i+7k)%30] == t[i%30],   t[r] = q5[r%5] + q6[r%6]  (mod 26)
 * independent of q7 and of the T8 permutation.
 *
 * PK9's structural repeats (2026-10-02 analysis):
 *   lag 7:  trigram UQG at i=119..121 (vs 126..128)  -> r = 29,0,1
 *           bigram  XG  at i=82,83                    -> r = 22,23
 *           bigram  GU  at i=90,91                    -> r = 0,1 (dup)
 *   lag 7 singles: i = 17,20,25,58,65,109,123
 *   lag 28 matches: i = 41,55,57,65,75,82,85,91,97,98,107,111
 *   lag 21 matches: i = 5,26,30,60,72,78,89,98
 *
 * Hard constraints (trigram + XG bigram — jointly far beyond chance):
 *   H1 t[6]=t[29], H2 t[7]=t[0], H3 t[8]=t[1], H4 t[29]=t[22], H5 t[0]=t[23]
 * Soft: the singles above; ranked count reported.
 *
 * Build: cc -O3 -o /tmp/constraint_search_pk9_wheels \
 *          kryptos/constraint_search_pk9_wheels.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define A 26
static const char ALPHA[A] = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int kidx[256];

/* constraint = (a1,b1,a2,b2): q5[a1]+q6[b1] == q5[a2]+q6[b2] */
typedef struct { int a1, b1, a2, b2; } Con;

static const Con HARD[5] = {
    {1, 0, 4, 5},  /* H1 t[6]=t[29]   */
    {2, 1, 0, 0},  /* H2 t[7]=t[0]    */
    {3, 2, 1, 1},  /* H3 t[8]=t[1]    */
    {4, 5, 2, 4},  /* H4 t[29]=t[22]  */
    {0, 0, 3, 5},  /* H5 t[0]=t[23]   */
};
static const Con SOFT[] = {
    /* lag-7 singles */
    {4, 0, 2, 5},  /* 17  */
    {2, 3, 0, 2},  /* 20  */
    {2, 2, 0, 1},  /* 25  */
    {0, 5, 3, 4},  /* 58  */
    {2, 0, 0, 5},  /* 65  */
    {1, 2, 4, 1},  /* 109 */
    {0, 4, 3, 3},  /* 123 */
    /* lag-28 */
    {4, 3, 1, 5},  /* 41  */
    {3, 5, 0, 1},  /* 55  */
    {0, 1, 2, 3},  /* 57  */
    {3, 3, 0, 5},  /* 65  */
    {3, 1, 0, 3},  /* 75  */
    {0, 2, 2, 4},  /* 82  */
    {4, 5, 1, 1},  /* 91  */
    {0, 5, 2, 1},  /* 97  */
    {1, 0, 3, 2},  /* 98  */
    {0, 3, 2, 5},  /* 107 */
    {4, 1, 1, 3},  /* 111 */
    /* lag-21 */
    {1, 2, 0, 5},  /* 5/26 */
    {1, 3, 0, 0},  /* 30/60 */
    {3, 3, 2, 0},  /* 72  */
    {4, 3, 3, 0},  /* 78  */
    {0, 2, 4, 5},  /* 89  */
    {4, 5, 3, 2},  /* 98  */
};
#define NSOFT ((int)(sizeof(SOFT) / sizeof(SOFT[0])))

#define MAXW 40000
static int w5[MAXW][5], w6[MAXW][6], n5, n6;
static char s5[MAXW][6], s6[MAXW][8];

static void load(const char *path, int wl[][5] /*or 6*/, char str[][6],
                 int *n, int len) {
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    char line[64];
    *n = 0;
    while (fgets(line, sizeof(line), f)) {
        char w[32]; int k = 0;
        for (char *s = line; *s && k < 31; s++)
            if (*s >= 'A' && *s <= 'Z') w[k++] = *s;
        w[k] = 0;
        if (k != len || *n >= MAXW) continue;
        for (int i = 0; i < len; i++) str[*n][i] = w[i];
        str[*n][len] = 0;
        if (len == 5) { for (int i = 0; i < 5; i++) wl[*n][i] = kidx[(unsigned char)w[i]]; }
        else { for (int i = 0; i < 6; i++) ((int (*)[6])wl)[*n][i] = kidx[(unsigned char)w[i]]; }
        (*n)++;
    }
    fclose(f);
    if (!*n) { fprintf(stderr, "no %d-letter words in %s\n", len, path); exit(2); }
}

int main(int argc, char **argv) {
    const char *f5 = argc > 1 ? argv[1] : "/tmp/pk9_w5.txt";
    const char *f6 = argc > 2 ? argv[2] : "/tmp/pk9_w6.txt";
    for (int i = 0; i < A; i++) kidx[(int)ALPHA[i]] = i;
    load(f5, w5, s5, &n5, 5);
    load(f6, (int (*)[5])w6, (char (*)[6])s6, &n6, 6);
    printf("5-letter words: %d, 6-letter words: %d, pairs: %.3g\n",
           n5, n6, (double)n5 * n6);

    long long tried = 0, passed = 0;
    int best = -1;
    for (int i = 0; i < n5; i++) {
        const int *q5 = w5[i];
        for (int j = 0; j < n6; j++) {
            const int *q6 = w6[j];
            tried++;
            int ok = 1;
            for (int c = 0; c < 5; c++) {
                const Con *C = &HARD[c];
                if ((q5[C->a1] + q6[C->b1]) % A != (q5[C->a2] + q6[C->b2]) % A) {
                    ok = 0; break;
                }
            }
            if (!ok) continue;
            passed++;
            int soft = 0;
            for (int c = 0; c < NSOFT; c++) {
                const Con *C = &SOFT[c];
                if ((q5[C->a1] + q6[C->b1]) % A == (q5[C->a2] + q6[C->b2]) % A) soft++;
            }
            if (soft >= best) {
                if (soft > best) { best = soft; printf("--- best soft = %d/%d ---\n", best, NSOFT); }
                printf("HARD+SOFT %2d/%d  %s + %s   q5=[%d,%d,%d,%d,%d] q6=[%d,%d,%d,%d,%d,%d]\n",
                       soft, NSOFT, s5[i], s6[j],
                       q5[0], q5[1], q5[2], q5[3], q5[4],
                       q6[0], q6[1], q6[2], q6[3], q6[4], q6[5]);
            }
        }
    }
    printf("tried %lld pairs, %lld passed 5 hard constraints (expected ~%.1f by chance)\n",
           tried, passed, tried / 11881376.0);
    return 0;
}

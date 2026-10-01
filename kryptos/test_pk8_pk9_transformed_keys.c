/*
 * Test whether PK9 literally reuses PK8's Q5/Q6/Q7 keyword coordinates after
 * independent cyclic phase changes and optional reversal of each wheel.
 *
 * Every 5-, 6-, and 7-wheel dihedral transform is combined with every one of
 * the 8! complete-columnar permutations. Both Q->T and T->Q layer orders are
 * scored. This is a finite PK8/PK9 bridge test, not a general PK9 attack.
 *
 * Build from repository root:
 *   cc -O3 -march=native -fopenmp -Wall -Wextra -Werror \
 *      kryptos/test_pk8_pk9_transformed_keys.c \
 *      -o /tmp/test_pk8_pk9_transformed_keys -lm
 */

#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define A 26
#define N 144
#define W 8
#define H 18
#define NPERM 40320
#define NVAR (2*5*2*6*2*7)
#define TOP 20
#define QSIZE (A*A*A*A)

static const char *KALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9 =
    "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXL"
    "EHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQ"
    "GLHDKEWSKAMHIJXD";
static const char *CONTROL =
    "ILEAVEATMIDNIGHTBEFOREGOINGIPICKUPONENEEDLEFROMTHEGUTTERIAMGRATEFUL"
    "TOMYTEACHERBUTTHEARCHIVEISMYTRUECALLINGANDTHEKNOTAWAITSILEAVETHEWHITESMITHASH";

static int kindex[256], to_std[A], ct[N];
static float *quad;
static unsigned char perms[NPERM][W]; /* ciphertext block at source column */
static int nperm;

typedef struct {
    float score;
    int order; /* 0 = Q then T; 1 = T then Q */
    int phase5, reverse5, phase6, reverse6, phase7, reverse7;
    unsigned char perm[W];
    char plain[N + 1];
} Hit;

static inline int qidx(int a, int b, int c, int d) {
    return ((a * A + b) * A + c) * A + d;
}

static float *load_quads(void) {
    float *table = calloc(QSIZE, sizeof(*table));
    if (!table) exit(2);
    FILE *f = popen("gzip -cd -- 'buttcrack/data/english_quadgrams.txt.gz'", "r");
    if (!f) { fprintf(stderr, "cannot load quadgrams\n"); exit(2); }
    char line[128], gram[8];
    long long count, total = 0;
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "%7s %lld", gram, &count) != 2 || strlen(gram) != 4) continue;
        int a = gram[0] - 'A', b = gram[1] - 'A', c = gram[2] - 'A', d = gram[3] - 'A';
        if (a < 0 || a >= A || b < 0 || b >= A || c < 0 || c >= A || d < 0 || d >= A) continue;
        table[qidx(a, b, c, d)] = (float)count;
        total += count;
    }
    if (pclose(f) != 0 || !total) { fprintf(stderr, "bad quadgram model\n"); exit(2); }
    float log_total = (float)log10((double)total);
    float floor_score = (float)log10(0.1 / (double)total);
    for (int i = 0; i < QSIZE; i++)
        table[i] = table[i] > 0 ? log10f(table[i]) - log_total : floor_score;
    return table;
}

static void gen_perm(int depth, unsigned used, unsigned char current[W]) {
    if (depth == W) {
        memcpy(perms[nperm++], current, W);
        return;
    }
    for (int block = 0; block < W; block++) if (!(used & (1u << block))) {
        current[depth] = (unsigned char)block;
        gen_perm(depth + 1, used | (1u << block), current);
    }
}

static void make_perms(void) {
    unsigned char current[W];
    gen_perm(0, 0, current);
    if (nperm != NPERM) { fprintf(stderr, "bad permutation count %d\n", nperm); exit(2); }
}

static inline int transformed(const int *wheel, int length, int phase, int reverse, int position) {
    int at = reverse ? phase - position : phase + position;
    at %= length;
    if (at < 0) at += length;
    return wheel[at];
}

static void make_key(int key[N], int p5, int r5, int p6, int r6, int p7, int r7) {
    static int w5[5], w6[6], w7[7], initialized;
    if (!initialized) {
        const char *s5 = "METER", *s6 = "METIER", *s7 = "MASTERY";
        for (int i = 0; i < 5; i++) w5[i] = kindex[(unsigned char)s5[i]];
        for (int i = 0; i < 6; i++) w6[i] = kindex[(unsigned char)s6[i]];
        for (int i = 0; i < 7; i++) w7[i] = kindex[(unsigned char)s7[i]];
        initialized = 1;
    }
    for (int i = 0; i < N; i++) {
        key[i] = (transformed(w5, 5, p5, r5, i) +
                  transformed(w6, 6, p6, r6, i) +
                  transformed(w7, 7, p7, r7, i)) % A;
    }
}

static float evaluate(const int source[N], const int key[N], const unsigned char perm[W],
                      int order, char plaintext[N + 1]) {
    int p[N];
    for (int i = 0; i < N; i++) {
        int row = i / W, col = i % W;
        int cpos = perm[col] * H + row;
        int value = order == 0 ? source[cpos] - key[i] : source[cpos];
        if (order == 1) value -= key[cpos];
        value %= A;
        if (value < 0) value += A;
        p[i] = to_std[value];
        plaintext[i] = (char)('A' + p[i]);
    }
    plaintext[N] = 0;
    float score = 0;
    for (int i = 0; i <= N - 4; i++) score += quad[qidx(p[i], p[i + 1], p[i + 2], p[i + 3])];
    return score / (N - 3);
}

static void insert(Hit top[TOP], const Hit *hit) {
    if (hit->score <= top[TOP - 1].score) return;
    int at = TOP - 1;
    while (at > 0 && hit->score > top[at - 1].score) {
        top[at] = top[at - 1];
        at--;
    }
    top[at] = *hit;
}

static int self_test(void) {
    int key[N], source[N], encrypted[N];
    unsigned char perm[W] = {3, 0, 7, 1, 6, 4, 2, 5};
    make_key(key, 2, 1, 3, 0, 4, 1);
    for (int i = 0; i < N; i++) source[i] = kindex[(unsigned char)CONTROL[i]];
    for (int i = 0; i < N; i++) {
        int row = i / W, col = i % W;
        encrypted[perm[col] * H + row] = (source[i] + key[i]) % A;
    }
    char recovered[N + 1];
    (void)evaluate(encrypted, key, perm, 0, recovered);
    int ok = !strcmp(recovered, CONTROL);
    printf("self_test_exact=%s\n", ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}

int main(int argc, char **argv) {
    int self = argc == 2 && !strcmp(argv[1], "--self-test");
    if (argc != 1 && !self) {
        fprintf(stderr, "usage: %s [--self-test]\n", argv[0]);
        return 2;
    }
    if (strlen(PK9) != N || strlen(CONTROL) != N) {
        fprintf(stderr, "internal length error\n");
        return 2;
    }
    memset(kindex, -1, sizeof(kindex));
    for (int i = 0; i < A; i++) {
        kindex[(unsigned char)KALPH[i]] = i;
        to_std[i] = KALPH[i] - 'A';
    }
    quad = load_quads();
    make_perms();
    for (int i = 0; i < N; i++) ct[i] = kindex[(unsigned char)PK9[i]];
    if (self) return self_test();

    Hit global[2][TOP];
    for (int order = 0; order < 2; order++)
        for (int i = 0; i < TOP; i++) global[order][i].score = -1e30f;

    double started = omp_get_wtime();
    #pragma omp parallel
    {
        Hit local[2][TOP];
        for (int order = 0; order < 2; order++)
            for (int i = 0; i < TOP; i++) local[order][i].score = -1e30f;

        #pragma omp for schedule(dynamic, 1)
        for (int variant = 0; variant < NVAR; variant++) {
            int x = variant;
            int r7 = x % 2; x /= 2;
            int p7 = x % 7; x /= 7;
            int r6 = x % 2; x /= 2;
            int p6 = x % 6; x /= 6;
            int r5 = x % 2; x /= 2;
            int p5 = x % 5;
            int key[N];
            make_key(key, p5, r5, p6, r6, p7, r7);
            for (int pi = 0; pi < NPERM; pi++) {
                for (int order = 0; order < 2; order++) {
                    Hit hit;
                    hit.score = evaluate(ct, key, perms[pi], order, hit.plain);
                    if (hit.score <= local[order][TOP - 1].score) continue;
                    hit.order = order;
                    hit.phase5 = p5; hit.reverse5 = r5;
                    hit.phase6 = p6; hit.reverse6 = r6;
                    hit.phase7 = p7; hit.reverse7 = r7;
                    memcpy(hit.perm, perms[pi], W);
                    insert(local[order], &hit);
                }
            }
        }
        #pragma omp critical
        for (int order = 0; order < 2; order++)
            for (int i = 0; i < TOP; i++) insert(global[order], &local[order][i]);
    }
    double elapsed = omp_get_wtime() - started;
    printf("variants=%d permutations=%d candidates_per_order=%lld elapsed=%.3fs\n",
           NVAR, NPERM, (long long)NVAR * NPERM, elapsed);

    for (int order = 0; order < 2; order++) {
        printf("\n%s\n", order == 0 ? "Q5+Q6+Q7 then T8" : "T8 then Q5+Q6+Q7");
        for (int rank = 0; rank < TOP; rank++) {
            Hit *h = &global[order][rank];
            printf("#%d score=%.6f q5=(phase=%d reverse=%d) q6=(phase=%d reverse=%d) "
                   "q7=(phase=%d reverse=%d) block_at_col=[",
                   rank + 1, h->score, h->phase5, h->reverse5, h->phase6, h->reverse6,
                   h->phase7, h->reverse7);
            for (int i = 0; i < W; i++) printf("%d%s", h->perm[i], i == W - 1 ? "]\n" : ",");
            printf("plaintext=%s\n", h->plain);
        }
    }
    return 0;
}

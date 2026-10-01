/*
 * Targeted PK9 attack: Q(7) + Q(6) + Q(5), then complete T(8).
 *
 * Hypothesis (encryption order):
 *
 *   P[i] --add q5[i%5]+q6[i%6]+q7[i%7] in the KRYPTOS alphabet--> Z
 *        --write rows of 8, read columns in an unknown order--> C
 *
 * This architecture is a concrete community lead, not an established fact.
 * The program keeps that distinction testable: --self-test first generates
 * ciphertext from the exact model and measures whether the attack recovers it;
 * the default run then applies the same frozen attack to official PK9.
 *
 * Build from the repository root:
 *   cc -O3 -march=native -fopenmp kryptos/attack_pk9_q567_t8.c \
 *      -o /tmp/attack_pk9_q567_t8 -lm
 *
 * Examples:
 *   /tmp/attack_pk9_q567_t8 --self-test --restarts 512 --steps 30000
 *   /tmp/attack_pk9_q567_t8 --restarts 4096 --steps 50000 --seed 20261001
 */

#include <ctype.h>
#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N 144
#define WIDTH 8
#define HEIGHT 18
#define A 26
#define QSIZE (A*A*A*A)
#define TSIZE (A*A*A)
#define BSIZE (A*A)

static const char *KALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9 =
    "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXL"
    "EHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQ"
    "GLHDKEWSKAMHIJXD";

/* Exactly 144 letters, drawn from the verified PK6 plaintext. */
static const char *CONTROL_PLAIN =
    "THEWHITESMITHSWORKSHOPISFILLEDWITHTHEOLDTOOLSOFHISTRADEMYEYESAREDRAWN"
    "TOTHEGUTTERALONGTHEWALLWHICHISSTREWNWITHEXQUISITENEEDLESTHEWHITESMITHSAYSHE";

static float *quad;
static float *tri;
static float *bigram;
static int kindex[256];
static int kalph_to_std[A];

typedef struct {
    uint64_t s;
} Rng;

typedef struct {
    /* Arbitrary-wheel mode fixes q5[0] and q6[0] as a gauge. Word mode uses
     * literal keyed-alphabet word values in all coordinates. */
    unsigned char q5[5], q6[6], q7[7];
    /* block_at_col[c] says which 18-letter ciphertext block fills grid col c. */
    unsigned char block_at_col[WIDTH];
    float objective;
    float quad_score;
    int pt[N];
} State;

typedef struct {
    char text[8];
    unsigned char value[7];
} Word;

#define MAX_WORDS 5000
static Word words5[MAX_WORDS], words6[MAX_WORDS], words7[MAX_WORDS];
static int nw5, nw6, nw7;

static inline uint64_t rng64(Rng *r) {
    uint64_t x = r->s;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    r->s = x;
    return x * UINT64_C(2685821657736338717);
}

static inline unsigned rnd(Rng *r, unsigned n) {
    return (unsigned)(rng64(r) % n);
}

static inline double uniform01(Rng *r) {
    return (rng64(r) >> 11) * (1.0 / 9007199254740992.0);
}

static inline int qidx(int a, int b, int c, int d) {
    return ((a * A + b) * A + c) * A + d;
}

static inline int tidx(int a, int b, int c) {
    return (a * A + b) * A + c;
}

static float *load_ngram(const char *path, int order, int table_size) {
    float *table = calloc((size_t)table_size, sizeof(*table));
    if (!table) {
        fprintf(stderr, "allocation failed for %s\n", path);
        exit(2);
    }

    /* Avoid a build-time libz dependency: gzip is already needed to inspect
     * the repository's model files. Paths are fixed constants, never input. */
    char command[512];
    snprintf(command, sizeof(command), "gzip -cd -- '%s'", path);
    FILE *f = popen(command, "r");
    if (!f) {
        fprintf(stderr, "cannot read %s (run from repository root)\n", path);
        exit(2);
    }
    char line[128], gram[8];
    long long count, total = 0;
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "%7s %lld", gram, &count) != 2 ||
            (int)strlen(gram) != order) continue;
        int x[4] = {0, 0, 0, 0}, ok = 1;
        for (int i = 0; i < order; i++) {
            x[i] = gram[i] - 'A';
            if (x[i] < 0 || x[i] >= A) ok = 0;
        }
        if (!ok) continue;
        int at;
        if (order == 4) at = qidx(x[0], x[1], x[2], x[3]);
        else if (order == 3) at = tidx(x[0], x[1], x[2]);
        else at = x[0] * A + x[1];
        table[at] = (float)count;
        total += count;
    }
    if (pclose(f) != 0 || !total) {
        fprintf(stderr, "empty or unreadable n-gram model: %s\n", path);
        exit(2);
    }
    float log_total = (float)log10((double)total);
    float floor_score = (float)log10(0.1 / (double)total);
    for (int i = 0; i < table_size; i++)
        table[i] = table[i] > 0.0f ? log10f(table[i]) - log_total : floor_score;
    return table;
}

static void init_models(void) {
    memset(kindex, -1, sizeof(kindex));
    for (int i = 0; i < A; i++) {
        kindex[(unsigned char)KALPH[i]] = i;
        kalph_to_std[i] = KALPH[i] - 'A';
    }
    quad = load_ngram("buttcrack/data/english_quadgrams.txt.gz", 4, QSIZE);
    tri = load_ngram("buttcrack/data/english_trigrams.txt.gz", 3, TSIZE);
    bigram = load_ngram("buttcrack/data/english_bigrams.txt.gz", 2, BSIZE);
}

static int load_words_one(const char *path, int length, Word *out) {
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    char line[128];
    int n = 0;
    while (fgets(line, sizeof(line), f) && n < MAX_WORDS) {
        char clean[8]; int k = 0;
        for (int i = 0; line[i] && k < 7; i++)
            if (line[i] >= 'A' && line[i] <= 'Z') clean[k++] = line[i];
        if (k != length) continue;
        clean[k] = 0;
        strcpy(out[n].text, clean);
        for (int i = 0; i < length; i++)
            out[n].value[i] = (unsigned char)kindex[(unsigned char)clean[i]];
        n++;
    }
    fclose(f);
    return n;
}

static void load_word_lists(void) {
    nw5 = load_words_one("kryptos/theophilus_w5.txt", 5, words5);
    nw6 = load_words_one("kryptos/theophilus_w6.txt", 6, words6);
    nw7 = load_words_one("kryptos/theophilus_w7.txt", 7, words7);
    printf("word lists: W5=%d W6=%d W7=%d\n", nw5, nw6, nw7);
}

static inline void set_word_state(State *s, int i5, int i6, int i7) {
    memcpy(s->q5, words5[i5].value, 5);
    memcpy(s->q6, words6[i6].value, 6);
    memcpy(s->q7, words7[i7].value, 7);
}

static inline float score_quad(const int *p) {
    float s = 0.0f;
    for (int i = 0; i <= N - 4; i++)
        s += quad[qidx(p[i], p[i+1], p[i+2], p[i+3])];
    return s / (float)(N - 3);
}

static inline float score_tri(const int *p) {
    float s = 0.0f;
    for (int i = 0; i <= N - 3; i++)
        s += tri[tidx(p[i], p[i+1], p[i+2])];
    return s / (float)(N - 2);
}

/*
 * Given wheel values, solve all 8! transposition orders exactly under the 126
 * within-row bigrams. DP state is (used ciphertext blocks, last block); the
 * destination column is popcount(mask)-1, so decryption remains phase-correct.
 * This removes the transposition permutation from the stochastic search rather
 * than asking annealing to discover clocks and column order simultaneously.
 */
static inline void evaluate(State *s, const int *ct) {
    int dec[WIDTH][WIDTH][HEIGHT]; /* [destination col][cipher block][row] */
    for (int c = 0; c < WIDTH; c++) {
        for (int b = 0; b < WIDTH; b++) {
            for (int r = 0; r < HEIGHT; r++) {
                int i = r * WIDTH + c;
                int key = s->q5[i % 5] + s->q6[i % 6] + s->q7[i % 7];
                int pk = (ct[b * HEIGHT + r] - key) % A;
                if (pk < 0) pk += A;
                dec[c][b][r] = kalph_to_std[pk];
            }
        }
    }

    float edge[WIDTH][WIDTH][WIDTH]; /* destination c, previous block, block */
    for (int c = 1; c < WIDTH; c++) {
        for (int a = 0; a < WIDTH; a++) {
            for (int b = 0; b < WIDTH; b++) {
                float v = 0.0f;
                if (a != b) {
                    for (int r = 0; r < HEIGHT; r++)
                        v += bigram[dec[c-1][a][r] * A + dec[c][b][r]];
                }
                edge[c][a][b] = v;
            }
        }
    }

    float dp[1 << WIDTH][WIDTH];
    signed char parent[1 << WIDTH][WIDTH];
    for (int m = 0; m < (1 << WIDTH); m++)
        for (int b = 0; b < WIDTH; b++) {
            dp[m][b] = -1e30f;
            parent[m][b] = -1;
        }
    for (int b = 0; b < WIDTH; b++) dp[1 << b][b] = 0.0f;

    for (int mask = 1; mask < (1 << WIDTH); mask++) {
        int used = __builtin_popcount((unsigned)mask);
        if (used >= WIDTH) continue;
        int c = used; /* destination column of the block being appended */
        for (int last = 0; last < WIDTH; last++) {
            float base = dp[mask][last];
            if (base < -1e20f) continue;
            for (int b = 0; b < WIDTH; b++) {
                if (mask & (1 << b)) continue;
                int nm = mask | (1 << b);
                float v = base + edge[c][last][b];
                if (v > dp[nm][b]) {
                    dp[nm][b] = v;
                    parent[nm][b] = (signed char)last;
                }
            }
        }
    }

    int mask = (1 << WIDTH) - 1;
    int last = 0;
    for (int b = 1; b < WIDTH; b++)
        if (dp[mask][b] > dp[mask][last]) last = b;
    s->objective = dp[mask][last] / (float)(HEIGHT * (WIDTH - 1));
    for (int c = WIDTH - 1; c >= 0; c--) {
        s->block_at_col[c] = (unsigned char)last;
        int previous = parent[mask][last];
        mask ^= 1 << last;
        last = previous;
    }

    for (int r = 0; r < HEIGHT; r++)
        for (int c = 0; c < WIDTH; c++)
            s->pt[r * WIDTH + c] = dec[c][s->block_at_col[c]][r];
    s->quad_score = score_quad(s->pt);
}

static void random_state(State *s, Rng *rng, const int *ct) {
    s->q5[0] = 0;
    s->q6[0] = 0;
    for (int i = 1; i < 5; i++) s->q5[i] = (unsigned char)rnd(rng, A);
    for (int i = 1; i < 6; i++) s->q6[i] = (unsigned char)rnd(rng, A);
    for (int i = 0; i < 7; i++) s->q7[i] = (unsigned char)rnd(rng, A);
    for (int i = 0; i < WIDTH; i++) s->block_at_col[i] = (unsigned char)i;
    for (int i = WIDTH - 1; i > 0; i--) {
        int j = (int)rnd(rng, (unsigned)i + 1);
        unsigned char t = s->block_at_col[i];
        s->block_at_col[i] = s->block_at_col[j];
        s->block_at_col[j] = t;
    }
    evaluate(s, ct);
}

/* Return a pointer to one of the 16 independent wheel coordinates. */
static unsigned char *coordinate(State *s, int j) {
    if (j < 4) return &s->q5[j + 1];
    j -= 4;
    if (j < 5) return &s->q6[j + 1];
    return &s->q7[j - 5];
}

static void mutate(State *s, Rng *rng) {
    /* evaluate() solves the permutation exactly, so only clocks are stochastic. */
    unsigned char *v = coordinate(s, (int)rnd(rng, 16));
    unsigned char old = *v;
    do { *v = (unsigned char)rnd(rng, A); } while (*v == old);
}

static void polish(State *s, Rng *rng, const int *ct) {
    /* Greedy all-values coordinate descent plus all permutation swaps. */
    for (int pass = 0; pass < 8; pass++) {
        float before = s->objective;
        int offset = (int)rnd(rng, 16);
        for (int z = 0; z < 16; z++) {
            unsigned char *v = coordinate(s, (z + offset) % 16);
            unsigned char original = *v, best_v = original;
            float best = s->objective;
            for (int x = 0; x < A; x++) {
                *v = (unsigned char)x;
                evaluate(s, ct);
                if (s->objective > best) {
                    best = s->objective;
                    best_v = (unsigned char)x;
                }
            }
            *v = best_v;
            evaluate(s, ct);
        }

        if (s->objective <= before + 1e-6f) break;
    }
}

static void anneal(State *s, Rng *rng, const int *ct, int steps) {
    State best = *s;
    for (int step = 0; step < steps; step++) {
        State next = *s;
        mutate(&next, rng);
        evaluate(&next, ct);

        /* Reheat every 5,000 moves. Mean-score deltas are usually < 0.2. */
        int phase = step % 5000;
        double frac = phase / 4999.0;
        double temp = 0.22 * pow(0.006 / 0.22, frac);
        double d = (double)next.objective - s->objective;
        if (d >= 0.0 || uniform01(rng) < exp(d / temp)) *s = next;
        if (s->objective > best.objective) best = *s;

        /* Begin each reheating cycle from the incumbent, then kick it. */
        if (phase == 4999) {
            *s = best;
            int kicks = 2 + (int)rnd(rng, 4);
            for (int k = 0; k < kicks; k++) mutate(s, rng);
            evaluate(s, ct);
        }
    }
    *s = best;
    polish(s, rng, ct);
}

static void print_state(const State *s, const char *label) {
    char text[N + 1];
    for (int i = 0; i < N; i++) text[i] = (char)('A' + s->pt[i]);
    text[N] = 0;
    printf("\n%s objective %.6f  quad %.6f\n", label, s->objective, s->quad_score);
    printf("q5=["); for (int i=0;i<5;i++) printf("%d%s",s->q5[i],i==4?"]\n":",");
    printf("q6=["); for (int i=0;i<6;i++) printf("%d%s",s->q6[i],i==5?"]\n":",");
    printf("q7=["); for (int i=0;i<7;i++) printf("%d%s",s->q7[i],i==6?"]\n":",");
    printf("block_at_col=[");
    for (int i=0;i<WIDTH;i++) printf("%d%s",s->block_at_col[i],i==WIDTH-1?"]\n":",");
    printf("plaintext=%s\n", text);
    fflush(stdout);
}

static void encrypt_control(int *ct) {
    /* Fixed, non-dictionary wheel values and nontrivial read order. */
    const int q5[5] = {11, 3, 24, 8, 17};
    const int q6[6] = {9, 21, 2, 14, 6, 25};
    const int q7[7] = {4, 19, 0, 23, 12, 7, 16};
    const int read_order[WIDTH] = {5, 1, 7, 0, 3, 6, 2, 4};
    int z[N];
    for (int i = 0; i < N; i++) {
        int p = kindex[(unsigned char)CONTROL_PLAIN[i]];
        z[i] = (p + q5[i%5] + q6[i%6] + q7[i%7]) % A;
    }
    int out = 0;
    for (int b = 0; b < WIDTH; b++) {
        int col = read_order[b];
        for (int r = 0; r < HEIGHT; r++) ct[out++] = z[r*WIDTH + col];
    }
}

static void encrypt_word_control(int *ct) {
    const char *w5 = "STEEL", *w6 = "SILVER", *w7 = "DRAWING";
    const int read_order[WIDTH] = {5, 1, 7, 0, 3, 6, 2, 4};
    int z[N], out = 0;
    for (int i = 0; i < N; i++) {
        int p = kindex[(unsigned char)CONTROL_PLAIN[i]];
        int key = kindex[(unsigned char)w5[i%5]] +
                  kindex[(unsigned char)w6[i%6]] +
                  kindex[(unsigned char)w7[i%7]];
        z[i] = (p + key) % A;
    }
    for (int b = 0; b < WIDTH; b++) {
        int col = read_order[b];
        for (int r = 0; r < HEIGHT; r++) ct[out++] = z[r*WIDTH + col];
    }
}

static int count_matches(const State *s, const char *truth) {
    int n = 0;
    for (int i = 0; i < N; i++) if (s->pt[i] == truth[i] - 'A') n++;
    return n;
}

static State run_word_search(const int *ct, int restarts, int steps, uint64_t seed,
                             const char *control_truth) {
    State global;
    global.objective = -1e30f;
    #pragma omp parallel
    {
        int tid = omp_get_thread_num();
        Rng rng = { seed ^ (UINT64_C(0x9e3779b97f4a7c15) * (uint64_t)(tid + 1)) };
        if (!rng.s) rng.s = 1;
        #pragma omp for schedule(dynamic, 1)
        for (int r = 0; r < restarts; r++) {
            int i5=(int)rnd(&rng,nw5), i6=(int)rnd(&rng,nw6), i7=(int)rnd(&rng,nw7);
            State s={0}; set_word_state(&s,i5,i6,i7); evaluate(&s,ct);
            State incumbent=s; int bi5=i5,bi6=i6,bi7=i7;

            /* Random whole-word annealing reaches across the nonlocal dictionary
             * space before deterministic alternating maximisation. */
            for(int step=0;step<steps;step++) {
                State next=s; int ni5=i5,ni6=i6,ni7=i7;
                int which=(int)rnd(&rng,3);
                if(which==0){ni5=(int)rnd(&rng,nw5);memcpy(next.q5,words5[ni5].value,5);}
                else if(which==1){ni6=(int)rnd(&rng,nw6);memcpy(next.q6,words6[ni6].value,6);}
                else {ni7=(int)rnd(&rng,nw7);memcpy(next.q7,words7[ni7].value,7);}
                evaluate(&next,ct);
                int phase=step%500;
                double frac=phase/499.0, temp=0.16*pow(0.004/0.16,frac);
                double d=next.objective-s.objective;
                if(d>=0 || uniform01(&rng)<exp(d/temp)) {s=next;i5=ni5;i6=ni6;i7=ni7;}
                if(s.objective>incumbent.objective){incumbent=s;bi5=i5;bi6=i6;bi7=i7;}
                if(phase==499){s=incumbent;i5=bi5;i6=bi6;i7=bi7;}
            }
            s=incumbent;i5=bi5;i6=bi6;i7=bi7;

            for(int pass=0;pass<5;pass++) {
                float before=s.objective;
                State best=s; int besti=i5;
                for(int x=0;x<nw5;x++){State c=s;memcpy(c.q5,words5[x].value,5);evaluate(&c,ct);if(c.objective>best.objective){best=c;besti=x;}}
                s=best;i5=besti;
                best=s;besti=i6;
                for(int x=0;x<nw6;x++){State c=s;memcpy(c.q6,words6[x].value,6);evaluate(&c,ct);if(c.objective>best.objective){best=c;besti=x;}}
                s=best;i6=besti;
                best=s;besti=i7;
                for(int x=0;x<nw7;x++){State c=s;memcpy(c.q7,words7[x].value,7);evaluate(&c,ct);if(c.objective>best.objective){best=c;besti=x;}}
                s=best;i7=besti;
                if(s.objective<=before+1e-6f)break;
            }

            #pragma omp critical
            {
                if(s.objective>global.objective) {
                    global=s;
                    char label[160];
                    snprintf(label,sizeof(label),"word best r=%d keys=%s/%s/%s%s",
                             r,words5[i5].text,words6[i6].text,words7[i7].text,
                             control_truth?" (control)":"");
                    print_state(&global,label);
                    if(control_truth)printf("matches=%d/%d\n",count_matches(&global,control_truth),N);
                }
            }
        }
    }
    return global;
}

static State run_search(const int *ct, int restarts, int steps, uint64_t seed,
                        const char *control_truth) {
    State global;
    global.objective = -1e30f;
    int updates = 0;

    #pragma omp parallel
    {
        State local_best;
        local_best.objective = -1e30f;
        int tid = omp_get_thread_num();
        Rng rng = { seed ^ (UINT64_C(0x9e3779b97f4a7c15) * (uint64_t)(tid + 1)) };
        if (!rng.s) rng.s = 1;

        #pragma omp for schedule(dynamic, 1)
        for (int r = 0; r < restarts; r++) {
            /* Restart-specific mixing makes the run reproducible for a fixed
             * thread count while avoiding nearby random streams. */
            rng.s ^= UINT64_C(0xd1b54a32d192ed03) * (uint64_t)(r + 1);
            State s;
            random_state(&s, &rng, ct);
            anneal(&s, &rng, ct, steps);
            if (s.objective > local_best.objective) local_best = s;

            #pragma omp critical
            {
                if (s.objective > global.objective) {
                    global = s;
                    updates++;
                    char label[96];
                    if (control_truth) {
                        snprintf(label, sizeof(label), "control best r=%d matches=%d/%d",
                                 r, count_matches(&s, control_truth), N);
                    } else {
                        snprintf(label, sizeof(label), "PK9 best r=%d update=%d", r, updates);
                    }
                    print_state(&global, label);
                }
            }
        }
    }
    return global;
}

int main(int argc, char **argv) {
    int self_test = 0, word_mode = 0, restarts = 512, steps = 30000;
    uint64_t seed = UINT64_C(20261001);
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--self-test")) self_test = 1;
        else if (!strcmp(argv[i], "--word-self-test")) { self_test = 1; word_mode = 1; }
        else if (!strcmp(argv[i], "--word-search")) word_mode = 1;
        else if (!strcmp(argv[i], "--restarts") && i+1 < argc) restarts = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--steps") && i+1 < argc) steps = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--seed") && i+1 < argc) seed = strtoull(argv[++i], NULL, 10);
        else {
            fprintf(stderr, "usage: %s [--self-test|--word-self-test|--word-search] [--restarts N] [--steps N] [--seed N]\n", argv[0]);
            return 2;
        }
    }
    if ((int)strlen(PK9) != N || (int)strlen(CONTROL_PLAIN) != N) {
        fprintf(stderr, "internal length error: PK9=%zu control=%zu\n",
                strlen(PK9), strlen(CONTROL_PLAIN));
        return 2;
    }
    init_models();
    if (word_mode) load_word_lists();

    int ct[N];
    const char *truth = NULL;
    if (self_test) {
        truth = CONTROL_PLAIN;
        State oracle = {0};
        if (word_mode) {
            encrypt_word_control(ct);
            printf("Positive word control: STEEL + SILVER + DRAWING, then complete T(8)\n");
            for(int i=0;i<5;i++)oracle.q5[i]=(unsigned char)kindex[(unsigned char)"STEEL"[i]];
            for(int i=0;i<6;i++)oracle.q6[i]=(unsigned char)kindex[(unsigned char)"SILVER"[i]];
            for(int i=0;i<7;i++)oracle.q7[i]=(unsigned char)kindex[(unsigned char)"DRAWING"[i]];
        } else {
            encrypt_control(ct);
            printf("Positive control: arbitrary Q(5)+Q(6)+Q(7), then complete T(8)\n");
            const unsigned char oq5[5] = {0,18,13,23,6};
            const unsigned char oq6[6] = {0,12,19,5,23,16};
            const unsigned char oq7[7] = {24,13,20,17,6,1,10};
            memcpy(oracle.q5, oq5, sizeof(oq5));
            memcpy(oracle.q6, oq6, sizeof(oq6));
            memcpy(oracle.q7, oq7, sizeof(oq7));
        }
        evaluate(&oracle, ct);
        print_state(&oracle, "ORACLE CONTROL (order re-solved by DP)");
        printf("oracle_accuracy=%d/%d\n", count_matches(&oracle, CONTROL_PLAIN), N);
    } else {
        for (int i = 0; i < N; i++) ct[i] = kindex[(unsigned char)PK9[i]];
        printf("Target: official PK9 under the Q(5)+Q(6)+Q(7) -> T(8) hypothesis\n");
    }
    printf("restarts=%d steps=%d threads=%d seed=%llu\n",
           restarts, steps, omp_get_max_threads(), (unsigned long long)seed);

    double t0 = omp_get_wtime();
    State best = word_mode ? run_word_search(ct, restarts, steps, seed, truth)
                           : run_search(ct, restarts, steps, seed, truth);
    double elapsed = omp_get_wtime() - t0;
    print_state(&best, self_test ? "FINAL CONTROL" : "FINAL PK9");
    printf("elapsed=%.3fs\n", elapsed);

    if (self_test) {
        int matches = count_matches(&best, CONTROL_PLAIN);
        printf("control_accuracy=%d/%d (%.2f%%)\n", matches, N, 100.0*matches/N);
        /* Exact plaintext, not exact gauge-equivalent keys, is the recovery gate. */
        return matches == N ? 0 : 1;
    }
    return 0;
}

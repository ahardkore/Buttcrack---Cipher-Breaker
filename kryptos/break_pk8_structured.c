/*
 * Blind structure-aware break of Paradigm Kryptos PK8.
 *
 * Assumptions supplied by the public clue and the established challenge family:
 *   - four sequential Quagmire III layers over the KRYPTOS alphabet;
 *   - keyword lengths 4, 5, 6, and 7;
 *   - "quite a lot of entropy, but some structure."
 *
 * This program interprets the structure as an insertion ladder for the first
 * three dictionary words: deleting one character from Q6 yields Q5, and
 * deleting one character from Q5 yields Q4. It does NOT contain PK8's plaintext
 * or any of its four keys. For each dictionary chain, Q7 is recovered directly
 * by seven independent monogram fits, then the complete plaintext is ranked by
 * English quadgrams.
 *
 * Build/run from repository root:
 *   cc -O3 -march=native -fopenmp -Wall -Wextra -Werror \
 *      kryptos/break_pk8_structured.c -o /tmp/break_pk8_structured -lm
 *   OMP_NUM_THREADS=32 /tmp/break_pk8_structured
 */

#define _POSIX_C_SOURCE 200809L

#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define A 26
#define N 153
#define TOP 20
#define QSIZE (A*A*A*A)
#define MAX_WORDS 100000

static const char *KALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8 =
    "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWO"
    "YIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUT"
    "HQCXNWPQZOIRJZGSWVPY";
static const char *CONTROL_PLAIN =
    "THEWHITESMITHSWORKSHOPISFILLEDWITHTHEOLDTOOLSOFHISTRADEMYEYESAREDRAWN"
    "TOTHEGUTTERALONGTHEWALLWHICHISSTREWNWITHEXQUISITENEEDLESTHEWHITESMITHS"
    "AYSHEMAKESONEE";

static int kindex[256], to_std[A], target_ct[N];
static double expected[A];
static float *quad;

typedef struct {
    char text[8];
} Word;

typedef struct {
    float score;
    char q4[5], q5[6], q6[7], q7[8], plain[N + 1];
} Hit;

static Word *words4, *words5, *words6;
static int n4, n5, n6;

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

static int compare_words(const void *a, const void *b) {
    return strcmp(((const Word *)a)->text, ((const Word *)b)->text);
}

static void add_words_from(const char *path, int length, Word *out, int *count) {
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        char clean[8];
        int n = 0, letters = 0;
        for (int i = 0; line[i]; i++) if (line[i] >= 'A' && line[i] <= 'Z') {
            letters++;
            if (n < 7) clean[n++] = line[i];
        }
        if (letters != length) continue;
        clean[n] = 0;
        if (*count >= MAX_WORDS) { fprintf(stderr, "too many words\n"); exit(2); }
        strcpy(out[(*count)++].text, clean);
    }
    fclose(f);
}

static int deduplicate(Word *words, int count) {
    qsort(words, (size_t)count, sizeof(*words), compare_words);
    int out = 0;
    for (int i = 0; i < count; i++) {
        if (out && !strcmp(words[i].text, words[out - 1].text)) continue;
        words[out++] = words[i];
    }
    return out;
}

static void load_words(void) {
    words4 = malloc(MAX_WORDS * sizeof(*words4));
    words5 = malloc(MAX_WORDS * sizeof(*words5));
    words6 = malloc(MAX_WORDS * sizeof(*words6));
    if (!words4 || !words5 || !words6) exit(2);
    add_words_from("kryptos/all_words.txt", 4, words4, &n4);
    add_words_from("kryptos/words_4.txt", 4, words4, &n4);
    add_words_from("kryptos/all_words.txt", 5, words5, &n5);
    add_words_from("kryptos/words_5.txt", 5, words5, &n5);
    add_words_from("kryptos/all_words.txt", 6, words6, &n6);
    add_words_from("kryptos/words_6.txt", 6, words6, &n6);
    n4 = deduplicate(words4, n4);
    n5 = deduplicate(words5, n5);
    n6 = deduplicate(words6, n6);
    printf("dictionary words: len4=%d len5=%d len6=%d\n", n4, n5, n6);
}

static const Word *find_word(const Word *words, int count, const char *text) {
    Word probe;
    strcpy(probe.text, text);
    return bsearch(&probe, words, (size_t)count, sizeof(*words), compare_words);
}

static void remove_at(const char *source, int length, int at, char *dest) {
    int out = 0;
    for (int i = 0; i < length; i++) if (i != at) dest[out++] = source[i];
    dest[out] = 0;
}

static void word_values(const char *word, int length, int *values) {
    for (int i = 0; i < length; i++) values[i] = kindex[(unsigned char)word[i]];
}

static void recover_q7(const int ct[N], const int q4[4], const int q5[5],
                       const int q6[6], int q7[7]) {
    int counts[7][A] = {{0}}, sizes[7] = {0};
    for (int i = 0; i < N; i++) {
        int residual = (ct[i] - q4[i % 4] - q5[i % 5] - q6[i % 6]) % A;
        if (residual < 0) residual += A;
        counts[i % 7][residual]++;
        sizes[i % 7]++;
    }
    for (int r = 0; r < 7; r++) {
        double best = 1e300;
        int best_shift = 0;
        for (int shift = 0; shift < A; shift++) {
            double chi = 0;
            for (int plain = 0; plain < A; plain++) {
                double want = expected[plain] * sizes[r];
                double diff = counts[r][(plain + shift) % A] - want;
                chi += diff * diff / want;
            }
            if (chi < best) { best = chi; best_shift = shift; }
        }
        q7[r] = best_shift;
    }
}

static float decrypt_score(const int ct[N], const int q4[4], const int q5[5],
                           const int q6[6], const int q7[7], char plain[N + 1]) {
    int p[N];
    for (int i = 0; i < N; i++) {
        int value = (ct[i] - q4[i % 4] - q5[i % 5] - q6[i % 6] - q7[i % 7]) % A;
        if (value < 0) value += A;
        p[i] = to_std[value];
        plain[i] = (char)('A' + p[i]);
    }
    plain[N] = 0;
    float score = 0;
    for (int i = 0; i <= N - 4; i++) score += quad[qidx(p[i], p[i + 1], p[i + 2], p[i + 3])];
    return score / (N - 3);
}

static void insert_hit(Hit top[TOP], const Hit *hit) {
    if (hit->score <= top[TOP - 1].score) return;
    int at = TOP - 1;
    while (at > 0 && hit->score > top[at - 1].score) {
        top[at] = top[at - 1];
        at--;
    }
    top[at] = *hit;
}

static Hit solve_chain(const int ct[N], const char *w4, const char *w5, const char *w6) {
    int q4[4], q5[5], q6[6], q7[7];
    word_values(w4, 4, q4);
    word_values(w5, 5, q5);
    word_values(w6, 6, q6);
    recover_q7(ct, q4, q5, q6, q7);
    Hit hit;
    strcpy(hit.q4, w4);
    strcpy(hit.q5, w5);
    strcpy(hit.q6, w6);
    for (int i = 0; i < 7; i++) hit.q7[i] = KALPH[q7[i]];
    hit.q7[7] = 0;
    hit.score = decrypt_score(ct, q4, q5, q6, q7, hit.plain);
    return hit;
}

static int self_test(void) {
    const char *w4 = "RATE", *w5 = "IRATE", *w6 = "PIRATE", *w7 = "CAPTAIN";
    int q4[4], q5[5], q6[6], q7[7], ct[N];
    word_values(w4, 4, q4); word_values(w5, 5, q5);
    word_values(w6, 6, q6); word_values(w7, 7, q7);
    for (int i = 0; i < N; i++) {
        ct[i] = (kindex[(unsigned char)CONTROL_PLAIN[i]] + q4[i % 4] + q5[i % 5] +
                 q6[i % 6] + q7[i % 7]) % A;
    }
    Hit hit = solve_chain(ct, w4, w5, w6);
    int ok = !strcmp(hit.q7, w7) && !strcmp(hit.plain, CONTROL_PLAIN);
    printf("self_test_exact=%s q4=%s q5=%s q6=%s q7=%s\n",
           ok ? "PASS" : "FAIL", hit.q4, hit.q5, hit.q6, hit.q7);
    return ok ? 0 : 1;
}

int main(int argc, char **argv) {
    int self = argc == 2 && !strcmp(argv[1], "--self-test");
    if (argc != 1 && !self) {
        fprintf(stderr, "usage: %s [--self-test]\n", argv[0]);
        return 2;
    }
    if (strlen(PK8) != N || strlen(CONTROL_PLAIN) != N) {
        fprintf(stderr, "internal length error\n");
        return 2;
    }
    memset(kindex, -1, sizeof(kindex));
    for (int i = 0; i < A; i++) {
        kindex[(unsigned char)KALPH[i]] = i;
        to_std[i] = KALPH[i] - 'A';
    }
    static const double english[26] = {
        .08167,.01492,.02782,.04253,.12702,.02228,.02015,.06094,.06966,.00153,
        .00772,.04025,.02406,.06749,.07507,.01929,.00095,.05987,.06327,.09056,
        .02758,.00978,.02360,.00150,.01974,.00074
    };
    for (int i = 0; i < A; i++) expected[i] = english[KALPH[i] - 'A'];
    quad = load_quads();
    for (int i = 0; i < N; i++) target_ct[i] = kindex[(unsigned char)PK8[i]];
    if (self) return self_test();
    load_words();

    Hit global[TOP];
    for (int i = 0; i < TOP; i++) global[i].score = -1e30f;
    long long chains = 0;
    double started = omp_get_wtime();

    #pragma omp parallel
    {
        Hit local[TOP];
        for (int i = 0; i < TOP; i++) local[i].score = -1e30f;
        long long local_chains = 0;

        #pragma omp for schedule(dynamic, 32)
        for (int i6 = 0; i6 < n6; i6++) {
            char seen5[6][6];
            int nseen5 = 0;
            for (int cut6 = 0; cut6 < 6; cut6++) {
                char w5[6];
                remove_at(words6[i6].text, 6, cut6, w5);
                int duplicate5 = 0;
                for (int j = 0; j < nseen5; j++) if (!strcmp(w5, seen5[j])) duplicate5 = 1;
                if (duplicate5 || !find_word(words5, n5, w5)) continue;
                strcpy(seen5[nseen5++], w5);

                char seen4[5][5];
                int nseen4 = 0;
                for (int cut5 = 0; cut5 < 5; cut5++) {
                    char w4[5];
                    remove_at(w5, 5, cut5, w4);
                    int duplicate4 = 0;
                    for (int j = 0; j < nseen4; j++) if (!strcmp(w4, seen4[j])) duplicate4 = 1;
                    if (duplicate4 || !find_word(words4, n4, w4)) continue;
                    strcpy(seen4[nseen4++], w4);
                    local_chains++;
                    Hit hit = solve_chain(target_ct, w4, w5, words6[i6].text);
                    insert_hit(local, &hit);
                }
            }
        }
        #pragma omp atomic
        chains += local_chains;
        #pragma omp critical
        {
            for (int i = 0; i < TOP; i++) insert_hit(global, &local[i]);
        }
    }

    double elapsed = omp_get_wtime() - started;
    printf("insertion_chains=%lld elapsed=%.3fs rate=%.3f chains/s\n",
           chains, elapsed, chains / elapsed);
    for (int i = 0; i < TOP; i++) if (global[i].score > -1e20f) {
        printf("\n#%d score=%.6f keys=%s/%s/%s/%s\nplaintext=%s\n",
               i + 1, global[i].score, global[i].q4, global[i].q5,
               global[i].q6, global[i].q7, global[i].plain);
    }

    free(words4); free(words5); free(words6); free(quad);
    return 0;
}

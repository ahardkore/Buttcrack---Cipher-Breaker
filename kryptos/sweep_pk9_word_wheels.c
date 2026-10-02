/*
 * sweep_pk9_word_wheels.c — exhaustive (wheel-word triple x T8) sweep for PK9.
 *
 * Architecture (verified against every solved PK puzzle, see
 * kryptos/verify_pk_constructions.py):
 *
 *   Q(7)Q(6)Q(5)T(8)  encryption order per the public notation:
 *     "qt" mode : P -> additive QuagmireIII sum q7[i%7]+q6[i%6]+q5[i%5]
 *                    over KRYPTOSABCDEFGHIJLMNQUVWXZ -> columnar T8
 *     "tq" mode : P -> columnar T8 -> additive QuagmireIII sum
 *
 * Columnar transposition (author convention, verified on PK2/PK4/PK5/PK6):
 * fill the 18x8 grid ROW-WISE, permute the columns by the keyword's
 * alphabetical order, read out COLUMN-BY-COLUMN.  We enumerate sigma with
 * sigma[k] = grid column emitted as output block k, over all 8! values or
 * only those induced by supplied 8-letter keywords.
 *
 * For every (sigma, w5, w6, w7) candidate the text is decrypted and scored
 * with the repository English quadgram model; a prefix-32 early-exit filter
 * (threshold -5.8/char, calibrated so every window of the verified story
 * texts passes) keeps the cost low.  Top hits are reported with keys.
 *
 * Modes:
 *   sweep_pk9_word_wheels W5FILE W6FILE W7FILE [--t8-words W8FILE]
 *                        [--order qt|tq|both] [--top N] [--report-above X]
 *   ... --keys W5 W6 W7 [T8WORD]     test one key hypothesis directly
 *   ... --self-test                   encryptor checks + planted control
 *
 * Build:
 *   cc -O3 -march=native -fopenmp -o /tmp/sweep_pk9_word_wheels \
 *      sweep_pk9_word_wheels.c -lm
 */

#include <ctype.h>
#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define A 26
#define N 144
#define W 8
#define H (N / W) /* 18 */
#define QSIZE (A * A * A * A)
#define NPERM 40320
#define MAXV 4096          /* max vocabulary entries per length */
#define PREFIX 32          /* early-exit prefix length */
#define PREFIX_THR (-5.8f) /* calibrated: min real-English window = -5.16 */

static const char *PK9_CT =
    "KSYAWFEYYOISZGEUFBLYATAIBY"
    "FAQBQYYVDWJKLJXMYIEPIFVHPQ"
    "NHZGSUHUUDXLEHRHUMALHEGLHX"
    "SJMUXGNUIVBXGUJHZRZGUSVHML"
    "SCTSUQXHSUMQQIFUQGKHJGUQGL"
    "HDKEWSKAMHIJXD";

/* Verified PK4 vectors (T(UNDERLAY) + Q(OCHRE) + Q(VERDIGRIS)) for the
 * encryptor self-test: if these do not round-trip, the conventions are
 * wrong and the sweep is meaningless. */
static const char *PK4_PT =
    "TWOYEARSINTHENEEDLESTRAILLEDMETOACRAFTSMANNAMEDTHEWHITESMITHONTHEROADTOHISA"
    "LPINEWORKSHOPIREREADHISPERFUNCTORYLETTERSHEMETMEATTHEGATESANDLEDMETOASTONE"
    "BARNSTACKEDWITHWINTERFODDERONEOFHISNEEDLESISHIDDENINTHEBARNIHAVEBEGUNTOWORK";
static const char *PK4_CT =
    "YOVISYUAFKUQNRJQLZTAZTMQOUKELJKCYUWIDSPSWRJRUEZNIFPUMUHQFFVBGOBEPWNTZGKVUT"
    "OVFSADUJUAYGWKQYOGNKHZVQMEWHSJGJFOBPHXKAPEXPWRJTSPSIJLCSXYTLDFBNZNPUAZNBZP"
    "KRFCUZDDZHZULZVPVWCXSIUVSCCFATGSJPNIGCJVTMUPTCGRTOFRXWCYKOMXOJKCECRUCKBDCIYJ";

/* Planted control: a story-consistent 144-letter "short letter". */
static const char *CONTROL_PT =
    "DEARTEACHERWHENIHAVEGONEDONOTGRIEVEITWASTENYEARSWELLSPENTIHAVETAKENONENEEDL"
    "EFROMTHEGUTTERANDIWILLNOTRETURNTHEARCHIVEISMYTRUECALLINGANDTHEKNOTAWAITSME"
    "GOODBYEYOURGRATEFULAPPRENTICEWHOWILLREADANYKNOT";
static const char *CONTROL_W5 = "AWAIT", *CONTROL_W6 = "GUTTER", *CONTROL_W7 = "TEACHER";
static const char *CONTROL_T8 = "GRATEFUL";

static const char KR[A + 1] = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int kindex[256];
static signed char to_std[A]; /* KRYPTOS index -> standard index */
static signed char to_kr[A];  /* standard index -> KRYPTOS index */

static float *quad;
static float *quad_big; /* bigram table derived from quadgrams (unused now) */
static float quad_max; /* maximum quadgram log-prob, for sound early abort */

/* permutations: sigma[k] = grid column emitted as block k */
static unsigned char perms[NPERM][W];
static int nperm_active;
static int active_perms[NPERM];
static char t8_word_by_perm[NPERM][12];

/* vocabularies */
static char v5[MAXV][16], v6[MAXV][16], v7[MAXV][16];
static int n5, n6, n7;
static signed char q5v[MAXV][5], q6v[MAXV][6], q7v[MAXV][7];

/* residue classes for each plaintext position */
static unsigned char cls5[N], cls6[N], cls7[N];

typedef struct {
    float score;
    int order_mode; /* 0 = qt, 1 = tq */
    int pi;
    char w5[16], w6[16], w7[16], t8[16];
    char plain[N + 1];
} Hit;

static void die(const char *m) { fprintf(stderr, "ERROR: %s\n", m); exit(2); }

static int qidx(int a, int b, int c, int d) { return ((a * A + b) * A + c) * A + d; }

static float *load_quads(void) {
    float *t = calloc(QSIZE, sizeof(*t));
    if (!t) die("oom");
    FILE *f = popen("gzip -cd -- 'buttcrack/data/english_quadgrams.txt.gz'", "r");
    if (!f) die("cannot load quadgrams (run from repo root)");
    char line[128], g[8];
    long long count, total = 0;
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "%7s %lld", g, &count) != 2 || strlen(g) != 4) continue;
        int a = g[0] - 'A', b = g[1] - 'A', c = g[2] - 'A', d = g[3] - 'A';
        if ((unsigned)a >= A || (unsigned)b >= A || (unsigned)c >= A || (unsigned)d >= A) continue;
        t[qidx(a, b, c, d)] = (float)count;
        total += count;
    }
    if (pclose(f) != 0 || !total) die("bad quadgram model");
    float lt = (float)log10((double)total), fl = (float)log10(0.1 / (double)total);
    float mx = -1e9f;
    for (int i = 0; i < QSIZE; i++) {
        t[i] = t[i] > 0 ? log10f(t[i]) - lt : fl;
        if (t[i] > mx) mx = t[i];
    }
    quad_max = mx;
    return t;
}

static void build_tables(void) {
    for (int i = 0; i < 256; i++) kindex[i] = -1;
    for (int i = 0; i < A; i++) {
        kindex[(unsigned char)KR[i]] = i;
        to_std[i] = (signed char)(KR[i] - 'A');
        to_kr[KR[i] - 'A'] = (signed char)i;
    }
    for (int i = 0; i < N; i++) {
        cls5[i] = (unsigned char)(i % 5);
        cls6[i] = (unsigned char)(i % 6);
        cls7[i] = (unsigned char)(i % 7);
    }
}

static void gen_perm_rec(int depth, unsigned used, unsigned char cur[W], unsigned char prm[][W],
                         int *cnt) {
    if (depth == W) {
        memcpy(prm[(*cnt)++], cur, W);
        return;
    }
    for (int b = 0; b < W; b++)
        if (!(used & (1u << b))) {
            cur[depth] = (unsigned char)b;
            gen_perm_rec(depth + 1, used | (1u << b), cur, prm, cnt);
        }
}

/* keyword-induced permutation: sigma[k] = column c with order[c] == k */
static void perm_from_keyword(const char *kw, unsigned char sigma[W]) {
    int n = (int)strlen(kw), order[16];
    for (int i = 0; i < n; i++) {
        int r = 0;
        for (int j = 0; j < n; j++)
            if (kw[j] < kw[i]) r++;
        order[i] = r;
    }
    for (int c = 0; c < n; c++) sigma[order[c]] = (unsigned char)c;
}

static void make_all_perms(void) {
    unsigned char cur[W];
    int cnt = 0;
    gen_perm_rec(0, 0, cur, perms, &cnt);
    if (cnt != NPERM) die("perm count");
    nperm_active = NPERM;
    for (int i = 0; i < NPERM; i++) {
        active_perms[i] = i;
        t8_word_by_perm[i][0] = 0;
    }
}

static int perm_rank(const unsigned char p[W]) {
    /* lexicographic rank */
    int r = 0;
    for (int i = 0; i < W; i++) {
        int smaller = 0;
        for (int j = i + 1; j < W; j++)
            if (p[j] < p[i]) smaller++;
        int fact = 1;
        for (int j = 2; j <= W - 1 - i; j++) fact *= j;
        r += smaller * fact;
    }
    return r;
}

static void load_t8_words(const char *path) {
    make_all_perms();
    char selected[NPERM];
    memset(selected, 0, sizeof(selected));
    FILE *f = fopen(path, "r");
    if (!f) die("cannot open t8 word file");
    char word[64];
    int words = 0;
    while (fscanf(f, "%63s", word) == 1) {
        for (char *c = word; *c; c++) *c = (char)toupper((unsigned char)*c);
        int ok = 1;
        for (const char *c = word; *c; c++)
            if (*c < 'A' || *c > 'Z') ok = 0;
        if (!ok || strlen(word) != W) continue;
        int dup = 0;
        for (int i = 0; word[i]; i++)
            for (int j = i + 1; word[j]; j++)
                if (word[i] == word[j]) dup = 1;
        if (dup) continue; /* author keys have distinct letters */
        unsigned char sigma[W];
        perm_from_keyword(word, sigma);
        int pi = perm_rank(sigma);
        if (pi < 0 || pi >= NPERM) die("rank");
        if (!selected[pi]) {
            selected[pi] = 1;
            snprintf(t8_word_by_perm[pi], sizeof(t8_word_by_perm[pi]), "%s", word);
        } else if (!t8_word_by_perm[pi][0]) {
            snprintf(t8_word_by_perm[pi], sizeof(t8_word_by_perm[pi]), "%s", word);
        }
        words++;
    }
    fclose(f);
    nperm_active = 0;
    for (int i = 0; i < NPERM; i++)
        if (selected[i]) active_perms[nperm_active++] = i;
    printf("T8 keyword filter: %d words -> %d distinct permutations\n", words, nperm_active);
}

static int load_vocab(const char *path, char v[][16], signed char *q, int len, int maxn) {
    FILE *f = fopen(path, "r");
    if (!f) die("cannot open vocab file");
    char word[64];
    int n = 0;
    while (fscanf(f, "%63s", word) == 1) {
        for (char *c = word; *c; c++) *c = (char)toupper((unsigned char)*c);
        if (strlen(word) != (size_t)len) continue;
        int ok = 1;
        for (const char *c = word; *c; c++)
            if (*c < 'A' || *c > 'Z') ok = 0;
        if (!ok) continue;
        if (n >= maxn) die("vocab too large");
        snprintf(v[n], 16, "%s", word);
        for (int i = 0; i < len; i++) q[n * len + i] = (signed char)kindex[(unsigned char)word[i]];
        n++;
    }
    fclose(f);
    return n;
}

/* ---- encryption (verified author conventions) -------------------------------- */

static void colt_encrypt(const char *in, int n, const unsigned char sigma[W], char *out) {
    /* grid row-wise with `cols` = W columns; block k of out = grid column
     * sigma[k].  For n = 224 (PK4) we use W = 8, H = 28: sigma maps blocks to
     * columns the same way. */
    int rows = n / W;
    /* out[k*rows + r] = in[sigma[k] + W*r] */
    for (int k = 0; k < W; k++)
        for (int r = 0; r < rows; r++) out[k * rows + r] = in[sigma[k] + W * r];
}

static void colt_decrypt(const char *in, int n, const unsigned char sigma[W], char *out) {
    int rows = n / W;
    for (int k = 0; k < W; k++)
        for (int r = 0; r < rows; r++) out[sigma[k] + W * r] = in[k * rows + r];
}

static void qsum_encrypt(const char *in, int n, const signed char *q5, const signed char *q6,
                         const signed char *q7, char *out) {
    for (int i = 0; i < n; i++) {
        int s = q5[i % 5] + q6[i % 6] + q7[i % 7];
        out[i] = KR[(kindex[(unsigned char)in[i]] + s) % A];
    }
}

static void qsum_decrypt_kr(const signed char *in, int n, const signed char *q5,
                            const signed char *q6, const signed char *q7, signed char *out) {
    for (int i = 0; i < n; i++)
        out[i] = (signed char)(((in[i] - q5[i % 5] - q6[i % 6] - q7[i % 7]) % A + A) % A);
}

/* ---- candidate evaluation ---------------------------------------------------- */

static inline float score_prefix(const signed char *p) {
    float s = 0;
    for (int i = 0; i + 3 < PREFIX; i++)
        s += quad[qidx(p[i], p[i + 1], p[i + 2], p[i + 3])];
    return s / (PREFIX - 3);
}

static inline float score_full(const signed char *p) {
    float s = 0;
    for (int i = 0; i + 3 < N; i++)
        s += quad[qidx(p[i], p[i + 1], p[i + 2], p[i + 3])];
    return s / (N - 3);
}

/* decrypt under (sigma, order_mode, wheels) -> standard-index plaintext */
static void decrypt_candidate(const signed char *ct_kr, const unsigned char sigma[W],
                              int order_mode, const signed char *q5, const signed char *q6,
                              const signed char *q7, signed char *p_std) {
    signed char buf[N];
    if (order_mode == 0) { /* qt: un-transpose then subtract */
        /* Z[sigma[k] + 8r] = ct[k*18 + r] */
        for (int k = 0; k < W; k++)
            for (int r = 0; r < H; r++) buf[sigma[k] + W * r] = ct_kr[k * H + r];
        for (int i = 0; i < N; i++)
            p_std[i] = to_std[(buf[i] - q5[i % 5] - q6[i % 6] - q7[i % 7] % A + 3 * A) % A];
    } else { /* tq: subtract then un-transpose */
        for (int i = 0; i < N; i++)
            buf[i] = (signed char)((ct_kr[i] - q5[i % 5] - q6[i % 6] - q7[i % 7] + 3 * A) % A);
        for (int k = 0; k < W; k++)
            for (int r = 0; r < H; r++) p_std[sigma[k] + W * r] = to_std[buf[k * H + r]];
    }
}

typedef struct {
    Hit hits[32];
    int n;
} TopList;

static void topl_add(TopList *t, Hit *h) {
    int pos = t->n;
    if (t->n < 32) t->n++;
    else {
        if (h->score <= t->hits[31].score) return;
        pos = 31;
    }
    while (pos > 0 && t->hits[pos - 1].score < h->score) {
        t->hits[pos] = t->hits[pos - 1];
        pos--;
    }
    t->hits[pos] = *h;
}

static void run_sweep(const signed char *ct_kr, int order_mode, TopList *global_top,
                      float report_above, long long *ncand) {
    long long cnt = 0;
#pragma omp parallel reduction(+ : cnt)
    {
    TopList local;
    local.n = 0;
#pragma omp for schedule(dynamic, 4)
    for (int pai = 0; pai < nperm_active; pai++) {
        int pi = active_perms[pai];
        const unsigned char *sigma = perms[pi];
        signed char zk[N]; /* un-transposed KRYPTOS-index stream (qt) or raw (tq) */
        if (order_mode == 0) {
            for (int k = 0; k < W; k++)
                for (int r = 0; r < H; r++) zk[sigma[k] + W * r] = ct_kr[k * H + r];
        } else {
            memcpy(zk, ct_kr, N);
        }
        /* base32[p] = zk[p] - q5 - q6 mod 26 for p < PREFIX+8 */
        signed char base[PREFIX + 8];
        signed char p_std[N];
        for (int i5 = 0; i5 < n5; i5++) {
            const signed char *q5 = q5v[i5];
            for (int i6 = 0; i6 < n6; i6++) {
                const signed char *q6 = q6v[i6];
                for (int p = 0; p < PREFIX + 8; p++)
                    base[p] = (signed char)((zk[p] - q5[cls5[p]] - q6[cls6[p]] + 2 * A) % A);
                for (int i7 = 0; i7 < n7; i7++) {
                    const signed char *q7 = q7v[i7];
                    cnt++;
                    /* stage 1: prefix score with sound running bound */
                    float ps = 0;
                    int abort1 = 0;
                    const int nq1 = PREFIX - 3;
                    for (int i = 0; i + 3 < PREFIX; i++) {
                        int a = to_std[(base[i] - q7[cls7[i]] + A) % A];
                        int b = to_std[(base[i + 1] - q7[cls7[i + 1]] + A) % A];
                        int c = to_std[(base[i + 2] - q7[cls7[i + 2]] + A) % A];
                        int d = to_std[(base[i + 3] - q7[cls7[i + 3]] + A) % A];
                        ps += quad[qidx(a, b, c, d)];
                        if (ps + (nq1 - 1 - i) * quad_max < PREFIX_THR * nq1) { abort1 = 1; break; }
                    }
                    if (abort1) continue;
                    ps /= nq1;
                    /* stage 2: full decryption */
                    decrypt_candidate(ct_kr, sigma, order_mode, q5, q6, q7, p_std);
                    float fs = score_full(p_std);
                    (void)report_above;
                    if (local.n == 32 && fs <= local.hits[31].score) continue;
                    Hit h;
                    h.score = fs;
                    h.order_mode = order_mode;
                    h.pi = pi;
                    snprintf(h.w5, 16, "%s", v5[i5]);
                    snprintf(h.w6, 16, "%s", v6[i6]);
                    snprintf(h.w7, 16, "%s", v7[i7]);
                    snprintf(h.t8, 16, "%s", t8_word_by_perm[pi]);
                    if (!h.t8[0]) {
                        strcpy(h.t8, "[perm]");
                        for (int i = 0; i < W; i++)
                            snprintf(h.t8 + strlen(h.t8), 16 - strlen(h.t8), "%d", sigma[i]);
                    }
                    for (int i = 0; i < N; i++) h.plain[i] = (char)('A' + p_std[i]);
                    h.plain[N] = 0;
                    topl_add(&local, &h);
                }
            }
        }
    } /* end for */
#pragma omp critical
    {
        for (int i = 0; i < local.n; i++) topl_add(global_top, &local.hits[i]);
    }
    } /* end parallel */
    *ncand += cnt;
    (void)report_above;
}

static void print_top(TopList *t, int order_both, float report_above) {
    printf("\n==== TOP %d HITS ====\n", t->n);
    for (int i = 0; i < t->n; i++) {
        Hit *h = &t->hits[i];
        printf("[%2d] %-7.4f  order=%s  Q5=%s Q6=%s Q7=%s  T8=%s\n", i, h->score,
               h->order_mode ? "tq" : "qt", h->w5, h->w6, h->w7, h->t8);
        printf("    %s\n", h->plain);
    }
}

static void to_kr_stream(const char *ct, signed char *out) {
    for (int i = 0; i < N; i++) out[i] = (signed char)kindex[(unsigned char)ct[i]];
}

static int self_test(void) {
    /* 1. encryptor reproduces official PK4 exactly */
    unsigned char sigma4[W];
    perm_from_keyword("UNDERLAY", sigma4);
    char mid[230];
    int n4 = (int)strlen(PK4_PT);
    colt_encrypt(PK4_PT, n4, sigma4, mid);
    signed char q5o[5], q9o[9];
    for (int i = 0; i < 5; i++) q5o[i] = (signed char)kindex[(unsigned char)"OCHRE"[i]];
    for (int i = 0; i < 9; i++) q9o[i] = (signed char)kindex[(unsigned char)"VERDIGRIS"[i]];
    for (int i = 0; i < n4; i++) mid[i] = KR[(kindex[(unsigned char)mid[i]] + q5o[i % 5] + q9o[i % 9]) % A];
    if (strncmp(mid, PK4_CT, n4) != 0) {
        printf("PK4 encryptor mismatch:\n  got %s\n  exp %s\n", mid, PK4_CT);
        return 1;
    }
    printf("[self-test] PK4 encryption reproduced exactly (%d chars)\n", n4);

    /* 2. planted PK9-style control recovered by the sweep machinery */
    unsigned char sigc[W];
    perm_from_keyword(CONTROL_T8, sigc);
    signed char q5c[5], q6c[6], q7c[7];
    for (int i = 0; i < 5; i++) q5c[i] = (signed char)kindex[(unsigned char)CONTROL_W5[i]];
    for (int i = 0; i < 6; i++) q6c[i] = (signed char)kindex[(unsigned char)CONTROL_W6[i]];
    for (int i = 0; i < 7; i++) q7c[i] = (signed char)kindex[(unsigned char)CONTROL_W7[i]];
    char zc[N], cc[N];
    qsum_encrypt(CONTROL_PT, N, q5c, q6c, q7c, zc);
    colt_encrypt(zc, N, sigc, cc);
    signed char ct_kr[N];
    to_kr_stream(cc, ct_kr);
    /* decrypt back */
    signed char p_std[N];
    decrypt_candidate(ct_kr, sigc, 0, q5c, q6c, q7c, p_std);
    for (int i = 0; i < N; i++)
        if (p_std[i] + 'A' != CONTROL_PT[i]) {
            printf("[self-test] control round-trip failed at %d\n", i);
            return 1;
        }
    printf("[self-test] control qt round-trip exact; control score = %.4f\n", score_full(p_std));

    /* sweep the control with the real vocabularies (must contain the keys);
     * restrict T8 to story keywords to keep the self-test fast (the sigma
     * arrays and scoring path are identical to the all-permutation mode) */
    load_t8_words("kryptos/pk9_vocab_story8.txt");
    TopList top = {0};
    long long nc = 0;
    run_sweep(ct_kr, 0, &top, -99.0f, &nc);
    unsigned char sigma_gr[W];
    perm_from_keyword(CONTROL_T8, sigma_gr);
    int found = 0;
    for (int i = 0; i < top.n; i++) {
        if (strcmp(top.hits[i].w5, CONTROL_W5) == 0 && strcmp(top.hits[i].w6, CONTROL_W6) == 0 &&
            strcmp(top.hits[i].w7, CONTROL_W7) == 0 &&
            !memcmp(perms[top.hits[i].pi], sigma_gr, W)) {
            printf("[self-test] control recovered at rank %d (score %.4f) of %lld candidates\n",
                   i + 1, top.hits[i].score, nc);
            found = 1;
            break;
        }
    }
    if (!found) {
        printf("[self-test] FAILED to recover planted control (top hit %.4f: %s/%s/%s %s)\n",
               top.n ? top.hits[0].score : -99.0f, top.n ? top.hits[0].w5 : "?",
               top.n ? top.hits[0].w6 : "?", top.n ? top.hits[0].w7 : "?",
               top.n ? top.hits[0].t8 : "?");
        print_top(&top, 0, -99.0f);
        return 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    build_tables();
    quad = load_quads();
    (void)quad_big;
    make_all_perms();

    const char *f5 = NULL, *f6 = NULL, *f7 = NULL, *f8 = NULL;
    int order_mode = 2; /* both */
    int want_top = 24;
    float report_above = -5.2f;
    const char *key5 = NULL, *key6 = NULL, *key7 = NULL, *key8 = NULL;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--t8-words") && i + 1 < argc) f8 = argv[++i];
        else if (!strcmp(argv[i], "--order") && i + 1 < argc) {
            order_mode = !strcmp(argv[i + 1], "qt") ? 0 : (!strcmp(argv[i + 1], "tq") ? 1 : 2);
            i++;
        } else if (!strcmp(argv[i], "--top") && i + 1 < argc) want_top = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--report-above") && i + 1 < argc) report_above = atof(argv[++i]);
        else if (!strcmp(argv[i], "--keys") && i + 4 < argc) {
            key5 = argv[++i]; key6 = argv[++i]; key7 = argv[++i];
            if (i + 1 < argc && argv[i + 1][0] != '-') key8 = argv[++i];
        } else if (!strcmp(argv[i], "--self-test")) {
            n5 = load_vocab("kryptos/pk9_vocab_story5.txt", v5, &q5v[0][0], 5, MAXV);
            n6 = load_vocab("kryptos/pk9_vocab_story6.txt", v6, &q6v[0][0], 6, MAXV);
            n7 = load_vocab("kryptos/pk9_vocab_story7.txt", v7, &q7v[0][0], 7, MAXV);
            printf("vocab: %d x %d x %d\n", n5, n6, n7);
            return self_test();
        } else if (!f5) f5 = argv[i];
        else if (!f6) f6 = argv[i];
        else if (!f7) f7 = argv[i];
        else die("unknown argument");
    }

    if (key5) {
        /* direct key test on real PK9 */
        signed char q5[5], q6[6], q7[7];
        for (int i = 0; i < 5; i++) q5[i] = (signed char)kindex[(unsigned char)key5[i]];
        for (int i = 0; i < 6; i++) q6[i] = (signed char)kindex[(unsigned char)key6[i]];
        for (int i = 0; i < 7; i++) q7[i] = (signed char)kindex[(unsigned char)key7[i]];
        signed char ct_kr[N];
        to_kr_stream(PK9_CT, ct_kr);
        unsigned char sigma[W];
        if (key8) perm_from_keyword(key8, sigma);
        for (int pi = 0; pi < 1; pi++) {
            (void)pi;
            signed char p_std[N];
            decrypt_candidate(ct_kr, key8 ? sigma : perms[0], 0, q5, q6, q7, p_std);
            /* if no T8 word given, sweep all perms for this wheel triple */
            TopList top = {0};
            long long nc = 0;
            if (!key8) {
                n5 = n6 = n7 = 1;
                snprintf(v5[0], 16, "%s", key5); memcpy(q5v[0], q5, 5);
                snprintf(v6[0], 16, "%s", key6); memcpy(q6v[0], q6, 6);
                snprintf(v7[0], 16, "%s", key7); memcpy(q7v[0], q7, 7);
                run_sweep(ct_kr, 0, &top, -99.0f, &nc);
                run_sweep(ct_kr, 1, &top, -99.0f, &nc);
                print_top(&top, 1, -99.0f);
            } else {
                decrypt_candidate(ct_kr, sigma, 0, q5, q6, q7, p_std);
                char pt[N + 1];
                for (int i = 0; i < N; i++) pt[i] = (char)('A' + p_std[i]);
                pt[N] = 0;
                printf("qt score %.4f: %s\n", score_full(p_std), pt);
                decrypt_candidate(ct_kr, sigma, 1, q5, q6, q7, p_std);
                for (int i = 0; i < N; i++) pt[i] = (char)('A' + p_std[i]);
                printf("tq score %.4f: %s\n", score_full(p_std), pt);
            }
        }
        return 0;
    }

    if (!f5 || !f6 || !f7) die("usage: sweep W5FILE W6FILE W7FILE [--t8-words F] [--order qt|tq|both]");
    n5 = load_vocab(f5, v5, &q5v[0][0], 5, MAXV);
    n6 = load_vocab(f6, v6, &q6v[0][0], 6, MAXV);
    n7 = load_vocab(f7, v7, &q7v[0][0], 7, MAXV);
    printf("vocab: %d x %d x %d = %lld triples\n", n5, n6, n7, (long long)n5 * n6 * n7);
    if (f8) load_t8_words(f8);
    printf("T8 permutations: %d\n", nperm_active);

    signed char ct_kr[N];
    to_kr_stream(PK9_CT, ct_kr);

    TopList top = {0};
    long long nc = 0;
    double t0 = omp_get_wtime();
    if (order_mode == 0 || order_mode == 2) run_sweep(ct_kr, 0, &top, report_above, &nc);
    if (order_mode == 1 || order_mode == 2) run_sweep(ct_kr, 1, &top, report_above, &nc);
    double dt = omp_get_wtime() - t0;
    printf("candidates: %lld in %.1fs (%.2fM/s)\n", nc, dt, nc / dt / 1e6);
    print_top(&top, order_mode == 2, report_above);
    return 0;
}

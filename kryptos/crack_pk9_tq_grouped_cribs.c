/* crack_pk9_tq_grouped_cribs.c — exact crib solver for PK9 under the TQ order
 * (columnar T(8) FIRST, then the Q(5)+Q(6)+Q(7) sum-clock).
 *
 * Model:  M = T8(P);  C[m] = M[m] + q5[m%5] + q6[m%6] + q7[m%7]  (mod 26)
 * Plaintext position i lives at M position m = order[i%8]*18 + i/8.
 * Crib letter P[o+j] = x gives the linear equation over Z26:
 *   q5[m_j%5] + q6[m_j%6] + q7[m_j%7] = Kidx(C[m_j]) - Kidx(x)
 * with m_j = order[(o+j)%8]*18 + (o+j)/8 — crib-independent given (order, o).
 *
 * Linear algebra over Z26 via CRT (mod 2 + mod 13, both fields):
 *   - The crib system has a 2-dim gauge (q5+a, q6+b, q7-a-b gives the same
 *     ciphertext); we fix it by adding rows q5[a*]=0, q6[b*]=0.
 *   - For L=30 letters, q6 residues covered are only ceil(30/8)=4 of 6, so
 *     2 q6 values are free in every crib; they are enumerated for survivors.
 *   - Per (order, offset) we precompute a crib-independent elimination plan
 *     for each field; per crib we apply it to the RHS, solve, and verify.
 *
 * Modes:
 *   --all-keys CRIBFILE              crib at offset 0
 *   --all-keys-all-offsets CRIBFILE  crib at every offset
 *   --self-test                      planted control (many random perms)
 *
 * Build: cc -O3 -march=native -fopenmp -o /tmp/crack_pk9_tq_grouped \
 *          kryptos/crack_pk9_tq_grouped_cribs.c -lm
 * Run from repo root.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define A 26
#define N 144
#define W 8
#define H 18
#define NV 18
#define NPERM 40320
#define QSIZE (A*A*A*A)
#define MAXC 40000
#define MAXL 64
#define NHIT 4000
#define MAXEQ (MAXL + 4)      /* crib rows + gauge rows + slack */
#define MAXOPS (MAXEQ * NV)

static const char *PK9_CT =
    "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMAL"
    "HEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static const char ALPHA[A] = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int kidx[256], to_std[A];
static float *quad;
static unsigned char perms[NPERM][W];
static int ct[N];

static inline int qidx4(int a, int b, int c, int d) {
    return ((a * A + b) * A + c) * A + d;
}
static float *load_quads(void) {
    float *t = calloc(QSIZE, sizeof(*t));
    if (!t) exit(2);
    FILE *f = popen("gzip -cd -- 'buttcrack/data/english_quadgrams.txt.gz'", "r");
    if (!f) { fprintf(stderr, "cannot load quadgrams\n"); exit(2); }
    char line[128], g[8]; long long count, total = 0;
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "%7s %lld", g, &count) != 2 || strlen(g) != 4) continue;
        int a = g[0]-'A', b = g[1]-'A', c = g[2]-'A', d = g[3]-'A';
        if (a<0||a>=A||b<0||b>=A||c<0||c>=A||d<0||d>=A) continue;
        t[qidx4(a,b,c,d)] = (float)count; total += count;
    }
    if (pclose(f) != 0 || !total) { fprintf(stderr, "bad quadgram model\n"); exit(2); }
    float lt = (float)log10((double)total), fl = (float)log10(0.1/(double)total);
    for (int i = 0; i < QSIZE; i++) t[i] = t[i] > 0 ? log10f(t[i]) - lt : fl;
    return t;
}
static void make_perms(void) {
    unsigned char p[W];
    for (int i = 0; i < W; i++) p[i] = i;
    int n = 0;
    for (;;) {
        memcpy(perms[n++], p, W);
        int i = W - 2;
        while (i >= 0 && p[i] >= p[i+1]) i--;
        if (i < 0) break;
        int j = W - 1;
        while (p[j] <= p[i]) j--;
        unsigned char t = p[i]; p[i] = p[j]; p[j] = t;
        for (int a = i+1, b = W-1; a < b; a++, b--) { t = p[a]; p[a] = p[b]; p[b] = t; }
    }
}

static char (*voc5)[8], (*voc6)[8], (*voc7)[8];
static int nv5, nv6, nv7;
static void load_voc(const char *path, char (**arr)[8], int *n, int len) {
    FILE *f = fopen(path, "r");
    if (!f) { *n = 0; return; }
    int cap = 1000; *n = 0;
    char (*a)[8] = malloc(cap * 8);
    char line[64];
    while (fgets(line, sizeof(line), f)) {
        char w[8]; int k = 0;
        for (char *s = line; *s && k < 7; s++) if (*s >= 'A' && *s <= 'Z') w[k++] = *s;
        w[k] = 0;
        if (k != len) continue;
        if (*n >= cap) { cap *= 2; a = realloc(a, cap * 8); }
        memcpy(a[(*n)++], w, 8);
    }
    fclose(f);
    *arr = a;
}

static char cribs[MAXC][MAXL + 1];
static int ncribs, criblen[MAXC];
static void load_cribs(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        char buf[256]; int n = 0;
        for (char *s = line; *s && n < MAXL; s++)
            if (*s >= 'A' && *s <= 'Z') buf[n++] = *s;
        if (n < 20) continue;
        buf[n] = 0;
        if (ncribs >= MAXC) { fprintf(stderr, "too many cribs\n"); exit(2); }
        memcpy(cribs[ncribs], buf, n + 1);
        criblen[ncribs] = n;
        ncribs++;
    }
    fclose(f);
    if (!ncribs) { fprintf(stderr, "no cribs\n"); exit(2); }
}

/* ---- per-perm elimination plan (one per field: p=2 and p=13) ------------- */
typedef struct {
    int p;                       /* field */
    int nrow, ncol;              /* rows = L+2 (crib+gauge), cols = nvar */
    int ops;                     /* number of rhs operations */
    int opdst[MAXOPS], opsrc[MAXOPS];
    int opf[MAXOPS];             /* factor */
    int npiv;                    /* pivot count = rank */
    int pivrow[NV], pivcol[NV], pivinv[NV];
    int nfree;
    int freecol[NV];
    /* check rows: rows that reduced to all-zero var coefficients;
     * each has residual y_r plus coefficients on free vars */
    int ncheck;
    int chkrow[MAXEQ];
    int chkfree[MAXEQ][NV];      /* coefficient per free var (mod p) */
    int pivfree[NV][NV];         /* pivot rows' free-var coefficients */
} Plan;

typedef struct {
    int ok, nvar, L;
    int slot[NV];                /* covered slot ids */
    int mpos[MAXL];
    unsigned char a[MAXL], b[MAXL], c[MAXL];
    int eqslot[MAXEQ][3], eqn[MAXEQ];   /* per row: slots (-1 if uncovered) */
    int gq5, gq6;                /* gauge rows reference these slots (col idx) */
    Plan pl2, pl13;
} Pre;

static int modinv_p(int v, int p) {
    for (int u = 1; u < p; u++) if ((v * u) % p == 1) return u;
    return -1;
}

static void plan_build(Plan *pl, int p, int nrow, int ncol,
                       const int eqslot[MAXEQ][3], const int eqn[MAXEQ]) {
    pl->p = p; pl->nrow = nrow; pl->ncol = ncol;
    static int M[MAXEQ][NV];
    memset(M, 0, sizeof(M));
    for (int r = 0; r < nrow; r++)
        for (int t = 0; t < eqn[r]; t++) M[r][eqslot[r][t]] = 1 % p;
    int rowp[MAXEQ];
    for (int r = 0; r < nrow; r++) rowp[r] = r;
    pl->ops = 0; pl->npiv = 0; pl->nfree = 0; pl->ncheck = 0;
    int usedrow[MAXEQ] = {0};
    for (int col = 0; col < ncol; col++) {
        int piv = -1;
        for (int r = pl->npiv; r < nrow; r++)
            if (M[rowp[r]][col]) { piv = r; break; }
        if (piv < 0) { pl->freecol[pl->nfree++] = col; continue; }
        if (piv != pl->npiv) { int t = rowp[pl->npiv]; rowp[pl->npiv] = rowp[piv]; rowp[piv] = t; }
        int pr = rowp[pl->npiv];
        int uinv = modinv_p(M[pr][col], p);
        pl->opdst[pl->ops] = pr; pl->opsrc[pl->ops] = -1; pl->opf[pl->ops] = uinv; pl->ops++;
        for (int j = 0; j < ncol; j++) M[pr][j] = (M[pr][j] * uinv) % p;
        M[pr][col] = 1 % p;
        for (int r = 0; r < nrow; r++) {
            if (r == pr) continue;
            int f = M[r][col];
            if (!f) continue;
            pl->opdst[pl->ops] = r; pl->opsrc[pl->ops] = pr; pl->opf[pl->ops] = f; pl->ops++;
            for (int j = 0; j < ncol; j++) {
                int v = M[r][j] - f * M[pr][j];
                v %= p; if (v < 0) v += p;
                M[r][j] = v;
            }
        }
        pl->pivrow[pl->npiv] = pr; pl->pivcol[pl->npiv] = col;
        usedrow[pr] = 1;
        pl->npiv++;
    }
    for (int pv = 0; pv < pl->npiv; pv++)
        for (int f = 0; f < pl->nfree; f++)
            pl->pivfree[pv][f] = M[pl->pivrow[pv]][pl->freecol[f]];
    /* every row not used as a pivot becomes a check row (its pivot-column
     * coefficients are zero by construction); only free columns remain */
    for (int r = 0; r < nrow; r++) {
        if (usedrow[r]) continue;
        int ci = pl->ncheck++;
        pl->chkrow[ci] = r;
        for (int f = 0; f < pl->nfree; f++) pl->chkfree[ci][f] = M[r][pl->freecol[f]];
    }
}


static void build_pre(Pre *pre, const unsigned char *order, int offset, int L) {
    pre->ok = 0;
    if (L > MAXL) L = MAXL;
    pre->L = L;
    for (int j = 0; j < L; j++) {
        int i = offset + j;
        int m = order[i % W] * H + i / W;
        pre->mpos[j] = m;
        pre->a[j] = (unsigned char)(m % 5);
        pre->b[j] = (unsigned char)(m % 6);
        pre->c[j] = (unsigned char)(m % 7);
    }
    int cover[NV]; memset(cover, 0, sizeof(cover));
    for (int j = 0; j < L; j++) {
        cover[pre->a[j]] = 1; cover[5 + pre->b[j]] = 1; cover[11 + pre->c[j]] = 1;
    }
    int nvar = 0;
    for (int v = 0; v < NV; v++) if (cover[v]) pre->slot[nvar++] = v;
    pre->nvar = nvar;
    if (nvar < 8) return;
    int g5 = -1, g6 = -1;
    for (int v = 0; v < 5; v++) if (cover[v]) { g5 = v; break; }
    for (int v = 5; v < 11; v++) if (cover[v]) { g6 = v; break; }
    if (g5 < 0 || g6 < 0) return;
    pre->gq5 = g5; pre->gq6 = g6;
    int slotpos[NV]; for (int v = 0; v < NV; v++) slotpos[v] = -1;
    for (int v = 0; v < nvar; v++) slotpos[pre->slot[v]] = v;
    int nrow = L + 2;
    for (int j = 0; j < L; j++) {
        int s[3] = { pre->a[j], 5 + pre->b[j], 11 + pre->c[j] };
        pre->eqn[j] = 0;
        for (int t = 0; t < 3; t++)
            if (slotpos[s[t]] >= 0) pre->eqslot[j][pre->eqn[j]++] = slotpos[s[t]];
    }
    pre->eqn[L] = 1;     pre->eqslot[L][0] = slotpos[g5];
    pre->eqn[L + 1] = 1; pre->eqslot[L + 1][0] = slotpos[g6];
    plan_build(&pre->pl2, 2, nrow, nvar, pre->eqslot, pre->eqn);
    plan_build(&pre->pl13, 13, nrow, nvar, pre->eqslot, pre->eqn);
    int c2 = 1; for (int f = 0; f < pre->pl2.nfree; f++) c2 *= 2;
    int c13 = 1; for (int f = 0; f < pre->pl13.nfree; f++) c13 *= 13;
    if (c2 > 4096 || c13 > 4096) return;   /* pathological; skip */
    pre->ok = 1;
}


/* apply plan to rhs y[0..nrow) mod p; on success fills xout (mod p) and
 * returns 1; returns 0 if no free assignment satisfies the check rows */
static int plan_solve(const Plan *pl, int p, const int *y, int *xout) {
    int yr[MAXEQ];
    for (int r = 0; r < pl->nrow; r++) { yr[r] = y[r] % p; if (yr[r] < 0) yr[r] += p; }
    for (int t = 0; t < pl->ops; t++) {
        int d = pl->opdst[t];
        if (pl->opsrc[t] < 0) yr[d] = (yr[d] * pl->opf[t]) % p;
        else {
            int v = yr[d] - pl->opf[t] * yr[pl->opsrc[t]];
            v %= p; if (v < 0) v += p;
            yr[d] = v;
        }
    }
    int x[NV];
    int nfree = pl->nfree, ncombo = 1;
    for (int f = 0; f < nfree; f++) ncombo *= p;
    for (int combo = 0; combo < ncombo; combo++) {
        int rem = combo;
        for (int f = 0; f < nfree; f++) { x[pl->freecol[f]] = rem % p; rem /= p; }
        int ok = 1;
        for (int pv = 0; pv < pl->npiv && ok; pv++) {
            int s = yr[pl->pivrow[pv]];
            for (int f = 0; f < nfree; f++)
                s -= pl->pivfree[pv][f] * x[pl->freecol[f]];
            s %= p; if (s < 0) s += p;
            x[pl->pivcol[pv]] = s;
        }
        for (int c = 0; c < pl->ncheck && ok; c++) {
            int s = yr[pl->chkrow[c]];
            for (int f = 0; f < nfree; f++)
                s += pl->chkfree[c][f] * x[pl->freecol[f]];
            if (s % p) ok = 0;
        }
        if (!ok) continue;
        for (int v = 0; v < pl->ncol; v++) xout[v] = x[v];
        return 1;
    }
    return 0;
}

/* full solve: returns 1 if the crib verifies; wheels[] filled mod 26 */
static int solve_crib(const Pre *pre, const char *crib, int L, unsigned char *wheels) {
    int y[MAXEQ];
    for (int j = 0; j < L; j++) {
        int m = pre->mpos[j];
        y[j] = (ct[m] - kidx[(unsigned char)crib[j]] + 2 * A) % A;
    }
    y[L] = 0; y[L + 1] = 0;   /* gauge rows */
    int x2[NV], x13[NV];
    if (!plan_solve(&pre->pl2, 2, y, x2)) return 0;
    if (!plan_solve(&pre->pl13, 13, y, x13)) return 0;
    /* CRT combine per covered slot */
    int xc[NV];
    for (int v = 0; v < pre->nvar; v++) {
        /* x = x13 + 13 * ((x2 - x13) * inv13 mod 2) */
        int t = ((x2[v] - x13[v]) % 2 + 2) % 2;   /* 13^{-1} mod 2 = 1 */
        xc[v] = (x13[v] + 13 * t) % A;
    }
    /* verify every crib letter mod 26 */
    int val[NV]; memset(val, 0, sizeof(val));
    for (int v = 0; v < pre->nvar; v++) val[pre->slot[v]] = xc[v];
    for (int j = 0; j < L; j++) {
        int m = pre->mpos[j];
        int v = (ct[m] - kidx[(unsigned char)crib[j]] + 2 * A) % A;
        if ((val[pre->a[j]] + val[5 + pre->b[j]] + val[11 + pre->c[j]]) % A != v)
            return 0;
    }
    memset(wheels, 0, NV);
    for (int v = 0; v < pre->nvar; v++) wheels[pre->slot[v]] = (unsigned char)xc[v];
    return 1;
}

static void decrypt_tq(const unsigned char *order, const unsigned char *x,
                       unsigned char *plain) {
    for (int i = 0; i < N; i++) {
        int m = order[i % W] * H + i / W;
        plain[i] = (unsigned char)((ct[m] + 3 * A - x[m % 5] - x[5 + m % 6] - x[11 + m % 7]) % A);
    }
}
static float score_plain(const unsigned char *p) {
    float s = 0;
    for (int i = 0; i <= N - 4; i++)
        s += quad[qidx4(to_std[p[i]], to_std[p[i+1]], to_std[p[i+2]], to_std[p[i+3]])];
    return s / N;
}

static void wheel_word(const unsigned char *x, int len, int off, char *out) {
    out[0] = 0;
    char (*voc)[8]; int n;
    if (len == 5) { voc = voc5; n = nv5; }
    else if (len == 6) { voc = voc6; n = nv6; }
    else { voc = voc7; n = nv7; }
    for (int i = 0; i < n; i++) {
        int ok = 1;
        for (int j = 0; j < len; j++)
            if (kidx[(unsigned char)voc[i][j]] != x[off + j]) { ok = 0; break; }
        if (ok) { strcpy(out, voc[i]); return; }
    }
}

/* ---- self test: plant wheels + perm, verify recovery across many perms ---- */
static int self_test(int verbose) {
    unsigned char x[NV];
    const char *q5w = "METER", *q6w = "METIER", *q7w = "MASTERY";
    for (int i = 0; i < 5; i++) x[i] = (unsigned char)kidx[(unsigned char)q5w[i]];
    for (int i = 0; i < 6; i++) x[5 + i] = (unsigned char)kidx[(unsigned char)q6w[i]];
    for (int i = 0; i < 7; i++) x[11 + i] = (unsigned char)kidx[(unsigned char)q7w[i]];
    const char *PT = "TENTHMONTHANDTHERESTLESSAUTUMNHASSETTLEDONTHBARNLIKEFALLINGSNOWTH"
                     "EWHITESMITHWORKSTHROUGHTHENIGHTANDIHEARTHEGUTTERNEEDLESTRIKING"
                     "THEANVILEVERYDAWNWITHOUTFAILTENYEARSINANDMYHANDS";
    unsigned char P[N], M[N];
    for (int i = 0; i < N; i++) P[i] = (unsigned char)kidx[(unsigned char)PT[i]];
    int save[N];
    memcpy(save, ct, sizeof(save));
    int npass = 0, ntrial = 0, nplan = 0;
    for (int t = 0; t < 60; t++) {
        unsigned char order[W];
        /* deterministic pseudo-random perm */
        unsigned rng = 77u + 13u * t;
        for (int i = 0; i < W; i++) order[i] = i;
        for (int i = W - 1; i > 0; i--) {
            rng = rng * 1103515245u + 12345u;
            int j = (rng >> 16) % (i + 1);
            unsigned char tmp = order[i]; order[i] = order[j]; order[j] = tmp;
        }
        for (int r = 0; r < H; r++)
            for (int c = 0; c < W; c++)
                M[order[c] * H + r] = P[8 * r + c];
        for (int m = 0; m < N; m++)
            ct[m] = (M[m] + x[m % 5] + x[5 + m % 6] + x[11 + m % 7]) % A;
        Pre pre;
        build_pre(&pre, order, 0, 48);
        ntrial++;
        if (!pre.ok) { if (verbose) printf("  perm %d: pre FAILED\n", t); continue; }
        nplan++;
        unsigned char w[NV], plain[N];
        if (!solve_crib(&pre, PT, 48, w)) {
            if (verbose) printf("  perm %d: solve FAILED\n", t);
            continue;
        }
        /* wheels are gauge-equivalent; decrypt must match exactly */
        decrypt_tq(order, w, plain);
        int ok = 1;
        for (int i = 0; i < N; i++) if (ALPHA[plain[i]] != PT[i]) ok = 0;
        if (ok) npass++; else if (verbose) printf("  perm %d: decrypt mismatch\n", t);
    }
    memcpy(ct, save, sizeof(save));
    printf("[self-test tq] %d/%d perms recovered (%d plans built)\n", npass, ntrial, nplan);
    return npass == ntrial && nplan == ntrial;
}

typedef struct { float score; int perm, ci, off; unsigned char x[NV]; char plain[N + 1]; } Hit;
static Hit hits[NHIT];
static int nhits;

int main(int argc, char **argv) {
    const char *cribfile = NULL;
    int all_offsets = 0, do_selftest = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--all-keys")) cribfile = argv[++i];
        else if (!strcmp(argv[i], "--all-keys-all-offsets")) { cribfile = argv[++i]; all_offsets = 1; }
        else if (!strcmp(argv[i], "--self-test")) do_selftest = 1;
        else { fprintf(stderr, "usage: %s --all-keys[-all-offsets] CRIBFILE | --self-test\n", argv[0]); return 1; }
    }
    for (int i = 0; i < A; i++) { kidx[(int)ALPHA[i]] = i; to_std[i] = ALPHA[i] - 'A'; }
    quad = load_quads();
    make_perms();
    load_voc("kryptos/pk9_vocab_broad5.txt", &voc5, &nv5, 5);
    load_voc("kryptos/pk9_vocab_broad6.txt", &voc6, &nv6, 6);
    load_voc("kryptos/pk9_vocab_broad7.txt", &voc7, &nv7, 7);
    if (do_selftest) {
        for (int i = 0; i < N; i++) ct[i] = kidx[(unsigned char)PK9_CT[i]];
        return self_test(1) ? 0 : 1;
    }
    if (getenv("DEBUG_ONE")) {
        unsigned char x[NV];
        const char *q5w = "METER", *q6w = "METIER", *q7w = "MASTERY";
        for (int i = 0; i < 5; i++) x[i] = (unsigned char)kidx[(unsigned char)q5w[i]];
        for (int i = 0; i < 6; i++) x[5 + i] = (unsigned char)kidx[(unsigned char)q6w[i]];
        for (int i = 0; i < 7; i++) x[11 + i] = (unsigned char)kidx[(unsigned char)q7w[i]];
        const char *PT = "TENTHMONTHANDTHERESTLESSAUTUMNHASSETTLEDONTHBARNLIKEFALLINGSNOWTH"
                         "EWHITESMITHWORKSTHROUGHTHENIGHTANDIHEARTHEGUTTERNEEDLESTRIKING"
                         "THEANVILEVERYDAWNWITHOUTFAILTENYEARSINANDMYHANDS";
        unsigned char P[N], M[N], order[W];
        for (int i = 0; i < N; i++) P[i] = (unsigned char)kidx[(unsigned char)PT[i]];
        int o0[W] = {5, 2, 7, 0, 4, 1, 6, 3};
        for (int i = 0; i < W; i++) order[i] = (unsigned char)o0[i];
        for (int r = 0; r < H; r++)
            for (int c = 0; c < W; c++)
                M[order[c] * H + r] = P[8 * r + c];
        for (int m = 0; m < N; m++)
            ct[m] = (M[m] + x[m % 5] + x[5 + m % 6] + x[11 + m % 7]) % A;
        Pre pre;
        build_pre(&pre, order, 0, 48);
        printf("pre.ok=%d nvar=%d L=%d\n", pre.ok, pre.nvar, pre.L);
        printf("pl2: ops=%d npiv=%d nfree=%d ncheck=%d\n",
               pre.pl2.ops, pre.pl2.npiv, pre.pl2.nfree, pre.pl2.ncheck);
        printf("pl13: ops=%d npiv=%d nfree=%d ncheck=%d\n",
               pre.pl13.ops, pre.pl13.npiv, pre.pl13.nfree, pre.pl13.ncheck);
        /* expected wheel values (gauge-shifted): plant is its own solution */
        int y[MAXEQ];
        for (int j = 0; j < 48; j++) {
            int m = pre.mpos[j];
            y[j] = (ct[m] - kidx[(unsigned char)PT[j]] + 2 * A) % A;
        }
        y[48] = 0; y[49] = 0;
        printf("expected check (plant wheels): ");
        for (int j = 0; j < 48; j++) {
            int m = pre.mpos[j];
            int v = (ct[m] - kidx[(unsigned char)PT[j]] + 2 * A) % A;
            int got = (x[pre.a[j]] + x[5 + pre.b[j]] + x[11 + pre.c[j]]) % A;
            if (got != v) printf("MISMATCH@%d ", j);
        }
        printf("\n");
        /* run plan_solve mod 2 on the planted y */
        int x2[NV], x13[NV];
        int ok2 = plan_solve(&pre.pl2, 2, y, x2);
        int ok13 = plan_solve(&pre.pl13, 13, y, x13);
        printf("plan_solve: mod2=%d mod13=%d\n", ok2, ok13);
        if (ok2 && ok13) {
            for (int v = 0; v < pre.nvar; v++) {
                int t = ((x2[v] - x13[v]) % 2 + 2) % 2;
                int xc = (x13[v] + 13 * t) % A;
                printf("slot %d: expect %d got %d\n", pre.slot[v], x[pre.slot[v]], xc);
            }
        }
        return 0;
    }
    if (!cribfile) { fprintf(stderr, "need crib file or --self-test\n"); return 1; }
    for (int i = 0; i < N; i++) ct[i] = kidx[(unsigned char)PK9_CT[i]];
    load_cribs(cribfile);
    int maxL = 0;
    for (int i = 0; i < ncribs; i++) if (criblen[i] > maxL) maxL = criblen[i];
    int maxoff = all_offsets ? N - 30 + 1 : 1;
    double t0 = omp_get_wtime();
    long long placements = 0, survivors = 0;

    for (int off = 0; off < maxoff; off++) {
        Pre *allpre = malloc((size_t)NPERM * sizeof(Pre));
        if (!allpre) { fprintf(stderr, "oom\n"); exit(2); }
        int nbad = 0;
#pragma omp parallel for schedule(static) reduction(+:nbad)
        for (int p = 0; p < NPERM; p++) {
            build_pre(&allpre[p], perms[p], off, maxL);
            if (!allpre[p].ok) nbad++;
        }
        long long pl = 0, sv = 0;
#pragma omp parallel for schedule(dynamic, 2) reduction(+:pl, sv)
        for (int ci = 0; ci < ncribs; ci++) {
            const char *crib = cribs[ci];
            int L = criblen[ci];
            unsigned char x[NV], plain[N];
            for (int p = 0; p < NPERM; p++) {
                if (!allpre[p].ok) continue;
                pl++;
                if (!solve_crib(&allpre[p], crib, L, x)) continue;
                sv++;
                /* enumerate free (uncovered) wheel slots for best score */
                int free_slots[NV], nfree = 0;
                int covered[NV] = {0};
                for (int u = 0; u < allpre[p].nvar; u++) covered[allpre[p].slot[u]] = 1;
                for (int v = 0; v < NV; v++) if (!covered[v]) free_slots[nfree++] = v;
                int nfree_combo = 1;
                for (int t = 0; t < nfree; t++) nfree_combo *= A;
                float f = -1e30f;
                unsigned char best_x[NV];
                for (int t = 0; t < nfree_combo; t++) {
                    int rem = t;
                    unsigned char xt[NV];
                    memcpy(xt, x, NV);
                    for (int q = 0; q < nfree; q++) { xt[free_slots[q]] = (unsigned char)(rem % A); rem /= A; }
                    decrypt_tq(perms[p], xt, plain);
                    float ft = score_plain(plain);
                    if (ft > f) { f = ft; memcpy(best_x, xt, NV); }
                }
                memcpy(x, best_x, NV);
                if (f <= -5.6f) continue;
#pragma omp critical
                {
                    if (nhits < NHIT) {
                        Hit *h = &hits[nhits++];
                        h->score = f; h->perm = p; h->ci = ci; h->off = off;
                        memcpy(h->x, x, NV);
                        for (int k = 0; k < N; k++) h->plain[k] = ALPHA[plain[k]];
                        h->plain[N] = 0;
                    }
                }
            }
        }
        placements += pl; survivors += sv;
        free(allpre);
        if (all_offsets) fprintf(stderr, "offset %d/%d done: placements=%lld survivors=%lld\n",
                                 off + 1, maxoff, placements, survivors);
    }
    printf("cribs=%d placements=%lld full-crib survivors=%lld elapsed=%.1fs\n",
           ncribs, placements, survivors, omp_get_wtime() - t0);
    for (int i = 0; i < nhits; i++)
        for (int j = i + 1; j < nhits; j++)
            if (hits[j].score > hits[i].score) { Hit t = hits[i]; hits[i] = hits[j]; hits[j] = t; }
    for (int i = 0; i < nhits && i < 20; i++) {
        Hit *h = &hits[i];
        char w5[16], w6[16], w7[16];
        /* gauge-sweep for word annotation */
        w5[0] = w6[0] = w7[0] = 0;
        for (int ga = 0; ga < A && !w5[0]; ga++)
            for (int gb = 0; gb < A; gb++) {
                unsigned char xt[NV];
                for (int v = 0; v < NV; v++) xt[v] = h->x[v];
                for (int v = 0; v < 5; v++) xt[v] = (unsigned char)((xt[v] + ga) % A);
                for (int v = 5; v < 11; v++) xt[v] = (unsigned char)((xt[v] + gb) % A);
                for (int v = 11; v < 18; v++) xt[v] = (unsigned char)((xt[v] + 2 * A - ga - gb) % A);
                wheel_word(xt, 5, 0, w5); wheel_word(xt, 6, 5, w6); wheel_word(xt, 7, 11, w7);
                if (w5[0] && w6[0] && w7[0]) { memcpy(h->x, xt, NV); goto done; }
            }
    done:;
        char ord[3 * W]; int o = 0;
        for (int c = 0; c < W; c++) o += sprintf(ord + o, "%d,", perms[h->perm][c]);
        ord[o - 1] = 0;
        printf("HIT %.4f crib#%d off=%d order=%s words=%s/%s/%s\n  q5=[%d,%d,%d,%d,%d] q6=[%d,%d,%d,%d,%d,%d] q7=[%d,%d,%d,%d,%d,%d,%d]\n  P=%s\n",
               h->score, h->ci, h->off, ord,
               w5[0] ? w5 : "-", w6[0] ? w6 : "-", w7[0] ? w7 : "-",
               h->x[0], h->x[1], h->x[2], h->x[3], h->x[4],
               h->x[5], h->x[6], h->x[7], h->x[8], h->x[9], h->x[10],
               h->x[11], h->x[12], h->x[13], h->x[14], h->x[15], h->x[16], h->x[17],
               h->plain);
    }
    if (!nhits) printf("no survivors above threshold\n");
    return 0;
}

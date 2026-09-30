/* Running-key drag: use a corpus as the keystream source for PK8 (or PK10).
 *
 * The puzzle author's hint for PK8: "the algorithm is simple; the key has a
 * lot of entropy but some structure."  A long book excerpt fits that perfectly:
 * maximal entropy per letter, but rigid, citable structure.  The annihilator
 * scan (sumclock_corpus_scan.py) answers "is the *plaintext* in this corpus?";
 * this answers the dual question, "is the *keystream* taken (with offset) from
 * this corpus?" -- K[t] = corpus[o + t] -- by decrypting with every offset and
 * quadgram-scoring the result.  A correct offset yields full English instantly
 * (score ~ -4.05); wrong offsets top out near -5.2 with rare exceptions.
 *
 * --selftest plants a corpus window as the true key and confirms the drag
 * recovers both the offset and a legible plaintext; without a working
 * control, the negative results would mean nothing.
 *
 * gcc -O3 -o pk8_running_key_drag pk8_running_key_drag.c -lm
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define MAXN 600

static const char *KTEXT = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *ATEXT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char *PK8 = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";
static char ctbuf[MAXN + 1];

/* --ct-file: a file whose first A-Z run is the ciphertext (from
   kryptos/pk_all_ciphertexts.json, e.g. via python3 -c). */

static float quad[26][26][26][26];
static int k2s[26];

static void load_quads(const char *path) {
    for (int a = 0; a < 26; a++) for (int b = 0; b < 26; b++)
        for (int c = 0; c < 26; c++) for (int d = 0; d < 26; d++)
            quad[a][b][c][d] = -9.5f;
    FILE *f = fopen(path, "r");
    if (!f) { fprintf(stderr, "cannot open %s\n", path); exit(1); }
    char q[32]; float sc;
    while (fscanf(f, "%31s %f", q, &sc) == 2)
        if (strlen(q) == 4) {
            int a=q[0]-'A', b=q[1]-'A', c=q[2]-'A', d=q[3]-'A';
            if ((unsigned)a<26&&(unsigned)b<26&&(unsigned)c<26&&(unsigned)d<26)
                quad[a][b][c][d] = sc;
        }
    fclose(f);
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    const char *alpha = KTEXT;
    const char *quads_path = "kryptos/english_quads.tsv";
    const char *corpus_path = "/tmp/pdfs/heididi_1.pdf.txt";
    const char *ct = PK8;
    const char *ct_file = NULL;
    int selftest = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--alpha") && i+1 < argc) alpha = (argv[++i][0]=='a') ? ATEXT : KTEXT;
        else if (!strcmp(argv[i], "--quads") && i+1 < argc) quads_path = argv[++i];
        else if (!strcmp(argv[i], "--corpus") && i+1 < argc) corpus_path = argv[++i];
        else if (!strcmp(argv[i], "--ct-file") && i+1 < argc) ct_file = argv[++i];
        else if (!strcmp(argv[i], "--selftest")) selftest = 1;
    }
    load_quads(quads_path);
    for (int i = 0; i < 26; i++) k2s[i] = alpha[i] - 'A';
    if (ct_file) {
        FILE *cf = fopen(ct_file, "r");
        if (!cf) { fprintf(stderr, "no ct file %s\n", ct_file); return 1; }
        size_t got = fread(ctbuf, 1, MAXN, cf);
        ctbuf[got] = 0; fclose(cf); ct = ctbuf;
    }

    /* corpus -> alphabet indices */
    FILE *f = fopen(corpus_path, "r");
    if (!f) { fprintf(stderr, "no corpus %s\n", corpus_path); return 1; }
    static int l2k[26];
    for (int i = 0; i < 26; i++) l2k[alpha[i]-'A'] = i;
    int cap = 1 << 22, nval = 0;
    int *vals = malloc(sizeof(int) * cap);
    int ch;
    while ((ch = fgetc(f)) != EOF) {
        if (ch >= 'a' && ch <= 'z') ch -= 32;
        if (ch >= 'A' && ch <= 'Z') {
            if (nval >= cap) { cap <<= 1; vals = realloc(vals, sizeof(int) * cap); }
            vals[nval++] = l2k[ch - 'A'];
        }
    }
    fclose(f);
    fprintf(stderr, "corpus letters: %d\n", nval);

    int ct_idx[MAXN], n = 0;
    for (const char *p = ct; *p && n < MAXN; p++) {
        const char *q = strchr(alpha, *p);
        if (q) ct_idx[n++] = (int)(q - alpha);
    }

    if (selftest) {
        /* plant: key = corpus[off..off+n), plaintext = fixed English window */
        const char *pt_txt =
            "THERAILWAYSTATIONATASHFORDWASCROWDEDWITHTRAVELLERSWAITINGFORTHEDELAYEXPRESSANDTHESTATIONMASTERWALKEDUPANDDOWNTHEPLATFORMWITHHISHANDSBEHINDHISBACKMUTTERINGABOUTTHEWEATHERANDTH";
        long off = nval / 3;
        for (int i = 0; i < n; i++) ct_idx[i] = (l2k[pt_txt[i]-'A'] + vals[off + i]) % 26;
        fprintf(stderr, "selftest: planted key offset %ld\n", off);
    }

    double gbest = -1e9; long goff = -1;
    double second = -1e9;
    static int pt[MAXN];
    for (long o = 0; o + n <= nval; o++) {
        double sc = 0.0;
        for (int i = 0; i < n; i++) pt[i] = k2s[(ct_idx[i] - vals[o + i] + 26) % 26];
        for (int i = 0; i + 4 <= n; i++) sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
        sc /= (n - 3);
        if (sc > gbest) { second = gbest; gbest = sc; goff = o; }
        else if (sc > second) second = sc;
    }
    printf("best offset %ld score %.4f | second %.4f\nPT: ", goff, gbest, second);
    long o = goff;
    for (int i = 0; i < n; i++) putchar('A' + k2s[(ct_idx[i] - vals[o + i] + 26) % 26]);
    putchar('\n');
    free(vals);
    return 0;
}

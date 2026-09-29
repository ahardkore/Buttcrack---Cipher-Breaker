#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *M_STR = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";
static int M[144];
static const int N = 144;

typedef struct {
    char word[16];
    int shifts[16];
    int len;
} Word;

static Word w3[300], w4[400], w5[500], w6[500], w7[600];
static int nw3 = 0, nw4 = 0, nw5 = 0, nw6 = 0, nw7 = 0;

static const char *raw_words[] = {
    // 3 letters
    "CIA", "DCI", "DOD", "KOT", "AGO", "ART", "EYE", "ROD", "AIR", "ICE", "ASH", "TIN", "PIN",
    "NET", "WEB", "LOG", "KEY", "ROW", "COL", "ARC", "RAY", "SUN", "DOT", "CAR", "CUT",
    // 4 letters
    "IRON", "WIRE", "ANVL", "BLOW", "COAL", "DRAW", "FIRE", "FILE", "FORG", "GLOW", "HEAT",
    "HEAR", "HOLE", "KNOT", "LEAD", "NEED", "PULL", "RING", "SEEK", "TOOL", "WORK", "CLAY",
    "CORD", "EYES", "PALE", "RODS", "RUST", "SLAG", "TONG", "WEFT", "WARP", "YARN", "ROSE",
    "FURL", "TIME", "LOGS", "ROUT", "LOST", "TRUE", "BOOK", "HAND", "PAGE", "READ", "TALE",
    "GOLD", "TOMB", "BASE", "CAMP", "WALL", "TREE", "WOOD", "SAND", "POOL", "WEST", "EAST",
    "DCIW", "CLCK", "ICON", "LINE", "ETCH", "CAST", "FORM", "GILD", "SEAL", "BIND", "GESO",
    "ROSE", "COLD", "FLAT", "HEAD", "PEEL", "FINE", "HARD", "SOFT", "WELD", "MELT", "DROP",
    // 5 letters
    "ANVIL", "BLADE", "CRAFT", "FORGE", "STEEL", "TONGS", "HEATH", "HEART", "FLAME", "SMOKE",
    "WATER", "METAL", "POINT", "PLIER", "PUNCH", "ROUND", "SHARP", "SHAPE", "SPLIT", "SWAGE",
    "TAPER", "TRACE", "TWIST", "WEAVE", "WHITE", "BLACK", "STONE", "STRIP", "KNOTS", "ORDER",
    "ROUTE", "INDEX", "FIRST", "SEVEN", "EIGHT", "HOLES", "RESID", "YEARS", "BERNE", "SWISS",
    "VIENN", "GESSO", "RELIC", "FOLIO", "PAPER", "PANEL", "GLAZE", "PIGMT", "BRUSH", "CHALK",
    "PAINT", "PRINT", "COLOR", "SHADE", "LIGHT", "FRAME", "MOUNT", "GRAIN", "FIBRE", "FIBER",
    "BEVEL", "DRAWN", "CRYPT", "NEEDL", "THRED", "NORTH", "SOUTH", "CLOCK", "CEDAR", "BIRCH",
    "GREEN", "TREES", "SHARK", "SCALE", "RIVER", "EARTH", "LUCID", "ALPHA", "OMEGA", "PIECE",
    "SHEET", "PLATE", "BLOCK", "STAMP", "PRESS", "CHILL", "ANNEAL",
    // 6 letters
    "NEEDLE", "THREAD", "HAMMER", "BELLOW", "HEARTH", "PUNCHS", "TEMPER", "QUENCH", "SILVER",
    "COPPER", "SMITHS", "ANVILS", "FURNAC", "CRUCIB", "SWAGES", "PLATES", "SOCKET", "GROOVE",
    "CHISEL", "PLIERS", "DRAWPL", "SPIDER", "SECRET", "RECORD", "LETTER", "LOGGED", "MASTER",
    "FRESCO", "MEDIUM", "BINDER", "PENCIL", "CRAYON", "PASTEL", "STUCCO", "MOSAIC", "RELIEF",
    "INTAGL", "MATRIX", "CAMERA", "LUCIDA", "OBSCUR", "PATINA", "PLAQUE", "BERLIN", "GRANIT",
    "QUARTZ", "SHADOW", "NUANCE", "SUBTLE", "ABSENC", "SLOWLY", "CANDLE", "THINGS", "DOORWY",
    "DEBRIS", "GRAVEL", "GROUND", "GARDEN", "SCHEDT", "SANBRN", "WEBSTR", "WOMACK", "CENTRE",
    "REDDIT", "WEAVER", "PINNER", "POWDER", "BURNIS", "POLISH", "SMOOTH",
    // 7 letters
    "NEEDLES", "THREADS", "BELLOWS", "CHISELS", "DRAWING", "FURNACE", "PUNCHES", "CRUCIBL",
    "HAMMERS", "TEMPERS", "QUENCHS", "ANNEALS", "SILVERS", "COPPERS", "ARCHIVE", "PELLEGR",
    "SCIENCE", "WHITESM", "TEXTILE", "SURGICA", "ANATOMI", "VIENNES", "BERNESE", "KRYPTOS",
    "EASTNOR", "WEBSTER", "WOMACKA", "SANBORN", "SCHEIDT", "LANGLEY", "VIRGINI", "PIGMENT",
    "CARTOON", "IMPASTO", "GLAZING", "SCRATCH", "ENGRAVE", "ETCHING", "CASTING", "MOLDING",
    "CARVING", "POTTERY", "CERAMIC", "ENAMELS", "PATINAS", "CRAQUEL", "VARNISH", "LACQUER",
    "SAMPLER", "PATTERN", "TAPESTR", "WEAVING", "SPINNING", "BLOWING", "MELTING", "HEATING",
    "PULLING", "SHAPING", "CUTTING", "FILINGS", "POINTED", "PIERCED", "RESIDUE", "MINUTES",
    "SECONDS", "DEGREES", "MEASURE", "SHADING", "ILLUSIO", "NUANCES", "PASSAGE", "WRITTEN",
    "STUDIED", "TENYEAR", "UNRAVEL", "ROBINSO", "PARADIG"
};

void add_word(const char *w) {
    int L = strlen(w);
    Word word;
    strcpy(word.word, w);
    word.len = L;
    for (int i = 0; i < L; i++) {
        word.shifts[i] = std_to_k[w[i] - 'A'];
    }
    if (L == 3 && nw3 < 300) w3[nw3++] = word;
    else if (L == 4 && nw4 < 400) w4[nw4++] = word;
    else if (L == 5 && nw5 < 500) w5[nw5++] = word;
    else if (L == 6 && nw6 < 500) w6[nw6++] = word;
    else if (L == 7 && nw7 < 600) w7[nw7++] = word;
}

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
    if (!f) { fprintf(stderr, "Cannot open quads\n"); exit(1); }
    char q[16];
    float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int c0 = q[0]-'A', c1 = q[1]-'A', c2 = q[2]-'A', c3 = q[3]-'A';
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
    for (int i = 0; i < N; i++) {
        M[i] = std_to_k[M_STR[i] - 'A'];
    }

    int n_raw = sizeof(raw_words) / sizeof(raw_words[0]);
    for (int i = 0; i < n_raw; i++) {
        add_word(raw_words[i]);
    }
    printf("Lexicon loaded: W3=%d, W4=%d, W5=%d, W6=%d, W7=%d\n", nw3, nw4, nw5, nw6, nw7);
}

void test_triple(Word *wa, int na, Word *wb, int nb, Word *wc, int nc, const char *label) {
    printf("\n--- Starting Sweep: %s (%d x %d x %d with all rotations) on M ---\n", label, na, nb, nc);
    float global_best = -999.0f;
    char global_hit[128];
    char global_pt[150];

    int pa = wa[0].len;
    int pb = wb[0].len;
    int pc = wc[0].len;

    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_hit[128];
        char local_pt[150];

        #pragma omp for schedule(dynamic)
        for (int ia = 0; ia < na; ia++) {
            for (int rota = 0; rota < pa; rota++) {
                int sa[16];
                for (int i = 0; i < pa; i++) sa[i] = wa[ia].shifts[(i + rota) % pa];

                for (int ib = 0; ib < nb; ib++) {
                    for (int rotb = 0; rotb < pb; rotb++) {
                        int sb[16];
                        for (int i = 0; i < pb; i++) sb[i] = wb[ib].shifts[(i + rotb) % pb];

                        for (int ic = 0; ic < nc; ic++) {
                            for (int rotc = 0; rotc < pc; rotc++) {
                                int sc_shift[16];
                                for (int i = 0; i < pc; i++) sc_shift[i] = wc[ic].shifts[(i + rotc) % pc];

                                // Quick test on first 16 chars
                                int pt16[16];
                                for (int i = 0; i < 16; i++) {
                                    int k = (sa[i % pa] + sb[i % pb] + sc_shift[i % pc]) % 26;
                                    int p_idx = (M[i] - k + 26) % 26;
                                    pt16[i] = k_to_std[p_idx];
                                }
                                float sc16 = 0.0f;
                                for (int i = 0; i < 13; i++) sc16 += quad_table[pt16[i]][pt16[i+1]][pt16[i+2]][pt16[i+3]];
                                sc16 /= 13.0f;
                                if (sc16 < -5.4f) continue;

                                // Full 144
                                int full_pt[144];
                                for (int i = 0; i < 144; i++) {
                                    int k = (sa[i % pa] + sb[i % pb] + sc_shift[i % pc]) % 26;
                                    int p_idx = (M[i] - k + 26) % 26;
                                    full_pt[i] = k_to_std[p_idx];
                                }
                                float full_sc = 0.0f;
                                for (int i = 0; i < 141; i++) full_sc += quad_table[full_pt[i]][full_pt[i+1]][full_pt[i+2]][full_pt[i+3]];
                                full_sc /= 141.0f;

                                if (full_sc > local_best) {
                                    local_best = full_sc;
                                    sprintf(local_hit, "%s(r%d)+%s(r%d)+%s(r%d)", wa[ia].word, rota, wb[ib].word, rotb, wc[ic].word, rotc);
                                    for (int i = 0; i < 144; i++) local_pt[i] = full_pt[i] + 'A';
                                    local_pt[144] = '\0';
                                }
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best > global_best) {
                global_best = local_best;
                strcpy(global_hit, local_hit);
                strcpy(global_pt, local_pt);
                printf("  [NEW BEST] sc=%.3f | %s | PT: %.50s...\n", global_best, global_hit, global_pt);
            }
        }
    }
    printf("Sweep %s Finished. Best: score=%.3f (%s)\n  PT: %s\n", label, global_best, global_hit, global_pt);
}

int main() {
    init();

    // 1. (W4, W5, W7) on M
    test_triple(w4, nw4, w5, nw5, w7, nw7, "(W4, W5, W7)");

    // 2. (W3, W5, W7) on M
    test_triple(w3, nw3, w5, nw5, w7, nw7, "(W3, W5, W7)");

    // 3. (W4, W6, W7) on M
    test_triple(w4, nw4, w6, nw6, w7, nw7, "(W4, W6, W7)");

    // 4. (W5, W6, W7) on M
    test_triple(w5, nw5, w6, nw6, w7, nw7, "(W5, W6, W7)");

    return 0;
}

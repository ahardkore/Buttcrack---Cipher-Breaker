#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

#define N 144
float quad_table[26*26*26*26];
int alph_to_std[26];

int get_idx(char c) {
    for (int i = 0; i < 26; i++) {
        if (ALPH[i] == c) return i;
    }
    return -1;
}

void load_quads() {
    for (int i = 0; i < 26*26*26*26; i++) quad_table[i] = -8.0f;
    for (int i = 0; i < 26; i++) alph_to_std[i] = ALPH[i] - 'A';

    FILE *f = fopen("/home/user/english_quads.tsv", "r");
    if (!f) exit(1);
    char line[128];
    while (fgets(line, sizeof(line), f)) {
        char q[5];
        float sc;
        if (sscanf(line, "%4s\t%f", q, &sc) == 2) {
            int c0 = q[0] - 'A', c1 = q[1] - 'A', c2 = q[2] - 'A', c3 = q[3] - 'A';
            if (c0>=0 && c0<26 && c1>=0 && c1<26 && c2>=0 && c2<26 && c3>=0 && c3<26) {
                int code = ((c0 * 26 + c1) * 26 + c2) * 26 + c3;
                quad_table[code] = sc;
            }
        }
    }
    fclose(f);
}

int main() {
    load_quads();
    int c_arr[N];
    for (int i = 0; i < N; i++) c_arr[i] = get_idx(CT[i]);

    const char *w4_list[] = {
        "IRON", "FIRE", "COAL", "HEAT", "BLOW", "BURN", "COLD", "TOOL",
        "MELT", "GLOW", "WORK", "GOLD", "LEAD", "WIRE", "DRAW", "HARD",
        "SOFT", "PULL", "DROP", "TINY", "FINE", "THIN", "EYES", "PALE",
        "SLOW", "DEEP", "TRUE", "CAST", "FORM", "POUR", "COOL", "HOLD",
        "SHUT", "OPEN", "FILL", "HAND", "TIME", "EAST", "WEST", "ROSE",
        "KNOT", "NEED", "SEAL", "BOOK", "PAGE", "READ", "LOCK", "CODE",
        "TEXT", "LINE", "WORD", "NAME", "SIGN", "MARK", "EDGE", "BOND",
        "CLOC", "NORD", "SUCH", "ONLY", "LAST", "DAYS", "YEAR", "MAKE",
        "TAKE", "TELL", "SAID", "SHOP", "WALL", "FALL", "LOST", "MADE",
        "DARK", "PURE", "BENT", "RODS", "TIPS", "HOLE", "TUBE", "STEM",
        NULL
    };

    const char *w5_list[] = {
        "FORGE", "HEART", "STEEL", "FLAME", "TONGS", "ANVIL", "BLAZE", "SMOKE",
        "ASHES", "POUND", "CRAFT", "SHAPE", "SHARP", "POINT", "SPLIT", "WHITE",
        "BLACK", "METAL", "BRASS", "ALLOY", "SMELT", "DRAWN", "PIECE", "PLATE",
        "SOLID", "CLEAN", "CLEAR", "SHINE", "GLOWS", "BURNS", "COALS", "TOOLS",
        "HEATS", "BLOWS", "WATER", "CHILL", "SPARK", "EMBER", "CRANE", "GRAIN",
        "FIBER", "WEAVE", "TWIST", "BOUND", "TRADE", "YEARS", "STUDY", "MAKER",
        "FIRST", "FINAL", "ORDER", "BERLIN", "CLOCK", "NORTH", "SOUTH", "LIGHT",
        "SHADE", "MAGIC", "KNOTS", "SKILL", "WATCH", "FORCE", "TEMPR", "SOLID",
        NULL
    };

    const char *w7_list[] = {
        "HAMMERS", "FURNACE", "BELLOWS", "CHARCOA", "DRAWING", "NEEDLES", "STUDENT",
        "TENYEAR", "MASTERS", "TRADESM", "SMITHYS", "CRAFTSM", "IRONWOR", "FORGING",
        "HEATING", "COOLING", "GLOWING", "BURNING", "PULLING", "CUTTING", "SHAPING",
        "MELTING", "POURING", "CASTING", "SLENDER", "THINNES", "FINERTH", "DELICAT",
        "PRECISI", "EXQUISI", "WORKSHP", "RESIDUE", "PRACTIC", "ARCHIVE", "PASSAGE",
        "LEAFLET", "STRINGS", "THREADS", "FIBREST", "MEASURE", "FURLONG", "KNOTTED",
        "UNRAVEL", "READING", "WRITING", "LETTERS", "SEVENTH", "FIFTEEN", "COUNTRY",
        "KRYPTOS", "EASTNNE", "WEBSTER", "WOMACKA", "HISTORC", "OBJECTS", "LOOKING",
        NULL
    };

    int n4 = 0, n5 = 0, n7 = 0;
    while (w4_list[n4]) n4++;
    while (w5_list[n5]) n5++;
    while (w7_list[n7]) n7++;

    printf("Testing %d x %d x %d = %d thematic triples...\n", n4, n5, n7, n4*n5*n7);

    float best_sc = -999.0f;
    char best_w4[16], best_w5[16], best_w7[16];
    char best_pt[N+1];

    for (int i4 = 0; i4 < n4; i4++) {
        int k4[4];
        for (int k = 0; k < 4; k++) k4[k] = get_idx(w4_list[i4][k]);

        for (int i5 = 0; i5 < n5; i5++) {
            int k5[5];
            for (int k = 0; k < 5; k++) k5[k] = get_idx(w5_list[i5][k]);

            for (int i7 = 0; i7 < n7; i7++) {
                int k7[7];
                for (int k = 0; k < 7; k++) k7[k] = get_idx(w7_list[i7][k]);

                // Quick prune on first 16 chars:
                float sc_quick = 0.0f;
                int pt_quick[16];
                for (int k = 0; k < 16; k++) {
                    int shift = (k4[k % 4] + k5[k % 5] + k7[k % 7]) % 26;
                    int p = (c_arr[k] - shift + 26) % 26;
                    pt_quick[k] = alph_to_std[p];
                }
                for (int k = 0; k < 13; k++) {
                    int code = ((pt_quick[k] * 26 + pt_quick[k+1]) * 26 + pt_quick[k+2]) * 26 + pt_quick[k+3];
                    sc_quick += quad_table[code];
                }
                sc_quick /= 13;
                if (sc_quick < -6.5f) continue; // prune unlikely prefixes

                // Full score:
                float sc = 0.0f;
                int pt_std[N];
                char pt_chars[N+1];
                for (int k = 0; k < N; k++) {
                    int shift = (k4[k % 4] + k5[k % 5] + k7[k % 7]) % 26;
                    int p = (c_arr[k] - shift + 26) % 26;
                    pt_std[k] = alph_to_std[p];
                    pt_chars[k] = ALPH[p];
                }
                pt_chars[N] = '\0';
                for (int k = 0; k < N - 3; k++) {
                    int code = ((pt_std[k] * 26 + pt_std[k+1]) * 26 + pt_std[k+2]) * 26 + pt_std[k+3];
                    sc += quad_table[code];
                }
                sc /= (N - 3);

                if (sc > best_sc) {
                    best_sc = sc;
                    strcpy(best_w4, w4_list[i4]);
                    strcpy(best_w5, w5_list[i5]);
                    strcpy(best_w7, w7_list[i7]);
                    strcpy(best_pt, pt_chars);
                    if (sc > -5.5f) {
                        printf("TRIPLE HIT: %s + %s + %s score=%.3f | PT: %s\n", best_w4, best_w5, best_w7, sc, pt_chars);
                    }
                }
            }
        }
    }

    printf("Best thematic triple: %s + %s + %s -> score=%.3f\n", best_w4, best_w5, best_w7, best_sc);
    printf("PT: %s\n", best_pt);
    return 0;
}

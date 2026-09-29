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

const char *words_4[] = {
    "KNOT", "HEAT", "FIRE", "HAND", "WORD", "TURN", "REAL", "ITEM", "BERN",
    "WALL", "TAKE", "DAYS", "TIME", "ONLY", "LOST", "ONCE", "HEAR", "LAST",
    "IRON", "WIRE", "DRAW", "PULL", "GOLD", "ANVL", "COLD", "TOOL", "MELT",
    "GLOW", "WORK", "LEAD", "HARD", "SOFT", "DROP", "TINY", "FINE", "THIN",
    "EYES", "PALE", "SLOW", "DEEP", "TRUE", "CAST", "FORM", "POUR", "COOL",
    "HOLD", "SHUT", "OPEN", "FILL", "EAST", "NORD", "WEST", "ROSE", "CLOC",
    NULL
};

const char *words_5[] = {
    "TRADE", "YEARS", "TOOLS", "STUDY", "MAKES", "COUNT", "SEVEN", "BOOKS",
    "MONTH", "SPLIT", "GLASS", "AGAIN", "PRIOR", "TRIED", "ROUTE", "PHRAS",
    "SHARE", "TOPIC", "SIXTH", "FORGE", "HEART", "STEEL", "FLAME", "TONGS",
    "ANVIL", "BLAZE", "SMOKE", "ASHES", "POUND", "CRAFT", "SHAPE", "SHARP",
    "POINT", "WHITE", "BLACK", "METAL", "BRASS", "ALLOY", "SMELT", "DRAWN",
    "PIECE", "PLATE", "SOLID", "CLEAN", "CLEAR", "SHINE", "GLOWS", "BURNS",
    "COALS", "HEATS", "BLOWS", "WATER", "CHILL", "SPARK", "EMBER", "GRAIN",
    "FIBER", "WEAVE", "TWIST", "BOUND", "MAKER", "FIRST", "FINAL", "ORDER",
    NULL
};

const char *words_6[] = {
    "NEEDLE", "HEARTH", "THREAD", "FAILED", "OBJECT", "LEGEND", "GUTTER",
    "MAKING", "BELLOW", "HAMMER", "SILVER", "SOLDER", "TEMPER", "QUENCH",
    "ANVILS", "COARSE", "FLAKES", "CHISEL", "PINCER", "FURNAC", "CRAFTS",
    NULL
};

const char *words_7[] = {
    "ARCHIVE", "LETTERS", "SEVENTH", "FIFTEEN", "NOTHING", "ADDRESS", "WRITTEN",
    "RECORDS", "PASSING", "RESIDUE", "HAMMERS", "FURNACE", "BELLOWS", "CHARCOA",
    "DRAWING", "NEEDLES", "STUDENT", "TENYEAR", "MASTERS", "TRADESM", "SMITHYS",
    "CRAFTSM", "IRONWOR", "FORGING", "HEATING", "COOLING", "GLOWING", "BURNING",
    "PULLING", "CUTTING", "SHAPING", "MELTING", "POURING", "CASTING", "SLENDER",
    "THINNES", "FINERTH", "DELICAT", "PRECISI", "EXQUISI", "WORKSHP", "PRACTIC",
    "LEAFLET", "STRINGS", "THREADS", "FIBREST", "MEASURE", "FURLONG", "KNOTTED",
    "UNRAVEL", "READING", "COUNTRY", "KRYPTOS", "EASTNNE", "WEBSTER", "WOMACKA",
    NULL
};

int main() {
    load_quads();
    int c_arr[N];
    for (int i = 0; i < N; i++) c_arr[i] = get_idx(CT[i]);

    float best_sc = -999.0f;
    char best_desc[128] = "";
    char best_pt[N+1];

    // 1. Test all (W4, W7)
    printf("Testing (W4, W7)...\n");
    for (int i4 = 0; words_4[i4]; i4++) {
        int k4[4]; for (int k=0; k<4; k++) k4[k] = get_idx(words_4[i4][k]);
        for (int i7 = 0; words_7[i7]; i7++) {
            int k7[7]; for (int k=0; k<7; k++) k7[k] = get_idx(words_7[i7][k]);

            int pt_std[N];
            char pt_alph[N+1];
            for (int k = 0; k < N; k++) {
                int shift = (k4[k % 4] + k7[k % 7]) % 26;
                int p = (c_arr[k] - shift + 26) % 26;
                pt_std[k] = alph_to_std[p];
                pt_alph[k] = ALPH[p];
            }
            pt_alph[N] = '\0';

            float sc = 0.0f;
            for (int k = 0; k < N - 3; k++) {
                int code = ((pt_std[k] * 26 + pt_std[k+1]) * 26 + pt_std[k+2]) * 26 + pt_std[k+3];
                sc += quad_table[code];
            }
            sc /= (N - 3);

            if (sc > best_sc) {
                best_sc = sc;
                sprintf(best_desc, "%s + %s", words_4[i4], words_7[i7]);
                strcpy(best_pt, pt_alph);
                if (sc > -5.5f) printf("HIT: %s score=%.3f | %s\n", best_desc, sc, pt_alph);
            }
        }
    }

    // 2. Test all (W5, W7)
    printf("Testing (W5, W7)...\n");
    for (int i5 = 0; words_5[i5]; i5++) {
        int k5[5]; for (int k=0; k<5; k++) k5[k] = get_idx(words_5[i5][k]);
        for (int i7 = 0; words_7[i7]; i7++) {
            int k7[7]; for (int k=0; k<7; k++) k7[k] = get_idx(words_7[i7][k]);

            int pt_std[N];
            char pt_alph[N+1];
            for (int k = 0; k < N; k++) {
                int shift = (k5[k % 5] + k7[k % 7]) % 26;
                int p = (c_arr[k] - shift + 26) % 26;
                pt_std[k] = alph_to_std[p];
                pt_alph[k] = ALPH[p];
            }
            pt_alph[N] = '\0';

            float sc = 0.0f;
            for (int k = 0; k < N - 3; k++) {
                int code = ((pt_std[k] * 26 + pt_std[k+1]) * 26 + pt_std[k+2]) * 26 + pt_std[k+3];
                sc += quad_table[code];
            }
            sc /= (N - 3);

            if (sc > best_sc) {
                best_sc = sc;
                sprintf(best_desc, "%s + %s", words_5[i5], words_7[i7]);
                strcpy(best_pt, pt_alph);
                if (sc > -5.5f) printf("HIT: %s score=%.3f | %s\n", best_desc, sc, pt_alph);
            }
        }
    }

    // 3. Test all (W4, W5, W7)
    printf("Testing (W4, W5, W7)...\n");
    for (int i4 = 0; words_4[i4]; i4++) {
        int k4[4]; for (int k=0; k<4; k++) k4[k] = get_idx(words_4[i4][k]);
        for (int i5 = 0; words_5[i5]; i5++) {
            int k5[5]; for (int k=0; k<5; k++) k5[k] = get_idx(words_5[i5][k]);
            for (int i7 = 0; words_7[i7]; i7++) {
                int k7[7]; for (int k=0; k<7; k++) k7[k] = get_idx(words_7[i7][k]);

                int pt_std[N];
                char pt_alph[N+1];
                for (int k = 0; k < N; k++) {
                    int shift = (k4[k % 4] + k5[k % 5] + k7[k % 7]) % 26;
                    int p = (c_arr[k] - shift + 26) % 26;
                    pt_std[k] = alph_to_std[p];
                    pt_alph[k] = ALPH[p];
                }
                pt_alph[N] = '\0';

                float sc = 0.0f;
                for (int k = 0; k < N - 3; k++) {
                    int code = ((pt_std[k] * 26 + pt_std[k+1]) * 26 + pt_std[k+2]) * 26 + pt_std[k+3];
                    sc += quad_table[code];
                }
                sc /= (N - 3);

                if (sc > best_sc) {
                    best_sc = sc;
                    sprintf(best_desc, "%s + %s + %s", words_4[i4], words_5[i5], words_7[i7]);
                    strcpy(best_pt, pt_alph);
                    if (sc > -5.5f) printf("HIT: %s score=%.3f | %s\n", best_desc, sc, pt_alph);
                }
            }
        }
    }

    printf("\nDone testing. Best overall: %s with score=%.3f\n", best_desc, best_sc);
    printf("PT: %s\n", best_pt);
    return 0;
}

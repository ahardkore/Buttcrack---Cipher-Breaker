#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *CT9 = "HEAQVHGZJGSYHEUBYFHJSQNHSEHAWFLHXAQBLQGZGSMLSEZYSJMQYYLHDUHLCPSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSEUFBVBXJXMMHIRHUKQQLYAGUJYIEJXDMALIFUTAIHZRPFF";
static int C[144];
static const int N = 144;

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
        C[i] = std_to_k[CT9[i] - 'A'];
    }
}

static const char *w4_list[] = {
    "EAST", "WEST", "SLOW", "TOMB", "GOLD", "MINE", "CAMP", "DOOR", "HEAD", "WALL",
    "HAND", "TREE", "BEAM", "RAYS", "LINE", "GRID", "CODE", "SEAL", "TIME", "TRUE",
    "NOTE", "CLUE", "NODE", "KNOT", "POLE", "IRON", "WIRE", "FIRE", "COAL", "HEAT",
    "ANNE", "FORG", "CAST", "BLOW", "LEAD", "TOOL", "BEAT", "LENS", "RODS", "SHOE",
    "WORK", "WOOD", "DIAL", "HOUR", "ZERO", "PURE", "PULL", "BORE", "FILE", "DRAW"
};
static const int n4 = sizeof(w4_list)/sizeof(w4_list[0]);

static const char *w5_list[] = {
    "CLOCK", "SHIPS", "NORTH", "SOUTH", "LIGHT", "SHADE", "FIELD", "EARTH", "DEBRI",
    "CANDL", "ANVIL", "STEEL", "FLAME", "TONGS", "HEART", "FORGE", "WATER", "SMOKE",
    "BLACK", "WHITE", "BRASS", "POINT", "SHARP", "TAPER", "METAL", "CHISE", "BERLN",
    "MEDOW", "RADII", "ABSCI", "SCALE", "STONE", "GAUGE", "PLIERS", "TWIST", "FRAME",
    "LAYER", "CRAFT", "TIGHT", "KNOTS", "ROUND", "PLATE", "DRIFT", "POUND", "SMELT"
};
static const int n5 = sizeof(w5_list)/sizeof(w5_list[0]);

static const char *w6_list[] = {
    "PORTAL", "BERLIN", "COPPER", "LANGLE", "SHADOW", "HIDDEN", "SECRET", "CRAFTY",
    "WEAVER", "BOBBIN", "SHUTTL", "SPINDL", "PLIERS", "CHISEL", "ANNEAL", "TEMPER",
    "PUNCHS", "SILVER", "BELLOW", "NEEDLE", "HEARTH", "HAMMER", "WINDLE", "WIMBLE",
    "NIMBLE", "TROWEL", "FURNAC", "CRUCIB", "BURNIS", "SOLDER", "GRAVER", "SCRIBE"
};
static const int n6 = sizeof(w6_list)/sizeof(w6_list[0]);

static const char *w7_list[] = {
    "KRYPTOS", "EASTNNE", "PALIMPS", "ABSCISS", "ORDINAT", "SEVENTH", "FIFTEEN",
    "FOURTEE", "SIXTEEN", "TWENTYF", "NIMBLES", "WIMBLES", "WINDLES", "TROWELS",
    "TONGSSS", "CHISELS", "PLIERSN", "SPINDLE", "THIMBLE", "SHUTTLE", "BOBBINS",
    "LOOMSSS", "WEAVERS", "SPINNER", "TAILORS", "QUENCHS", "TEMPERS", "ANNEALS",
    "FORGING", "CRUCIBL", "FURNACE", "CASTING", "PUNCHED", "SANBORN", "SCHEIDT",
    "LANGLEY", "BERLINS", "GERMANY", "AMERICA", "WEBSTER", "WOMACKA", "WILLIAM",
    "WHITESM", "WORKSHO", "DRAWPLT", "ANVILSS", "BELLOWS", "HAMMERS", "METALLS"
};
static const int n7 = sizeof(w7_list)/sizeof(w7_list[0]);

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    init();

    printf("Thematic vocab sizes: W4=%d, W5=%d, W6=%d, W7=%d\n", n4, n5, n6, n7);

    // Precompute shifts
    int s4[n4][4], s5[n5][5], s6[n6][6], s7[n7][7];
    for (int i = 0; i < n4; i++) for (int j = 0; j < 4; j++) s4[i][j] = std_to_k[w4_list[i][j] - 'A'];
    for (int i = 0; i < n5; i++) for (int j = 0; j < 5; j++) s5[i][j] = std_to_k[w5_list[i][j] - 'A'];
    for (int i = 0; i < n6; i++) for (int j = 0; j < 6; j++) s6[i][j] = std_to_k[w6_list[i][j] - 'A'];
    for (int i = 0; i < n7; i++) for (int j = 0; j < 7; j++) s7[i][j] = std_to_k[w7_list[i][j] - 'A'];

    float best_sc = -999.0f;
    char best_hit[128] = "";
    char best_pt[150] = "";

    // 1. Test 3-clock (4, 5, 7) with ALL phase rotations: 4 x 5 x 7 = 140 phases per triple
    printf("Evaluating 3-clock (4, 5, 7) across %d triples x 140 phases = %lld combos...\n",
           n4*n5*n7, (long long)n4*n5*n7*140);

    for (int i4 = 0; i4 < n4; i4++) {
        for (int i5 = 0; i5 < n5; i5++) {
            for (int i7 = 0; i7 < n7; i7++) {
                for (int rot4 = 0; rot4 < 4; rot4++) {
                    for (int rot5 = 0; rot5 < 5; rot5++) {
                        for (int rot7 = 0; rot7 < 7; rot7++) {
                            // Fast check first 16 letters
                            int pt[144];
                            for (int i = 0; i < 16; i++) {
                                int k = s4[i4][(i + rot4) & 3] + s5[i5][(i + rot5) % 5] + s7[i7][(i + rot7) % 7];
                                int p_idx = (C[i] - k) % 26;
                                if (p_idx < 0) p_idx += 26;
                                pt[i] = k_to_std[p_idx];
                            }
                            float sc = 0.0f;
                            for (int i = 0; i < 13; i++) sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                            sc /= 13.0f;
                            if (sc < -5.6f) continue;

                            for (int i = 16; i < 144; i++) {
                                int k = s4[i4][(i + rot4) & 3] + s5[i5][(i + rot5) % 5] + s7[i7][(i + rot7) % 7];
                                int p_idx = (C[i] - k) % 26;
                                if (p_idx < 0) p_idx += 26;
                                pt[i] = k_to_std[p_idx];
                            }
                            float full_sc = sc * 13.0f;
                            for (int i = 13; i < 141; i++) full_sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                            full_sc /= 141.0f;

                            if (full_sc > best_sc) {
                                best_sc = full_sc;
                                sprintf(best_hit, "%s(r%d) + %s(r%d) + %s(r%d)",
                                        w4_list[i4], rot4, w5_list[i5], rot5, w7_list[i7], rot7);
                                for (int i = 0; i < 144; i++) best_pt[i] = pt[i] + 'A';
                                best_pt[144] = '\0';
                                printf("New best: sc=%.3f | %s\nPT: %.60s...\n", full_sc, best_hit, best_pt);
                                fflush(stdout);
                            }
                        }
                    }
                }
            }
        }
    }

    printf("\n3-Clock search finished. Best score: %.3f (%s)\n", best_sc, best_hit);

    // 2. Test 4-clock (4, 5, 6, 7) without rotation (phase 0)
    printf("\nEvaluating 4-clock (4, 5, 6, 7) at phase 0 across %lld combos...\n",
           (long long)n4*n5*n6*n7);

    for (int i4 = 0; i4 < n4; i4++) {
        for (int i5 = 0; i5 < n5; i5++) {
            for (int i6 = 0; i6 < n6; i6++) {
                for (int i7 = 0; i7 < n7; i7++) {
                    int pt[144];
                    for (int i = 0; i < 16; i++) {
                        int k = s4[i4][i & 3] + s5[i5][i % 5] + s6[i6][i % 6] + s7[i7][i % 7];
                        int p_idx = (C[i] - k) % 26;
                        if (p_idx < 0) p_idx += 26;
                        pt[i] = k_to_std[p_idx];
                    }
                    float sc = 0.0f;
                    for (int i = 0; i < 13; i++) sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                    sc /= 13.0f;
                    if (sc < -5.6f) continue;

                    for (int i = 16; i < 144; i++) {
                        int k = s4[i4][i & 3] + s5[i5][i % 5] + s6[i6][i % 6] + s7[i7][i % 7];
                        int p_idx = (C[i] - k) % 26;
                        if (p_idx < 0) p_idx += 26;
                        pt[i] = k_to_std[p_idx];
                    }
                    float full_sc = sc * 13.0f;
                    for (int i = 13; i < 141; i++) full_sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                    full_sc /= 141.0f;

                    if (full_sc > best_sc) {
                        best_sc = full_sc;
                        sprintf(best_hit, "%s + %s + %s + %s",
                                w4_list[i4], w5_list[i5], w6_list[i6], w7_list[i7]);
                        for (int i = 0; i < 144; i++) best_pt[i] = pt[i] + 'A';
                        best_pt[144] = '\0';
                        printf("New best (4-clock): sc=%.3f | %s\nPT: %.60s...\n", full_sc, best_hit, best_pt);
                        fflush(stdout);
                    }
                }
            }
        }
    }

    printf("\nAll thematic tests complete. Best score: %.3f (%s)\n", best_sc, best_hit);
    printf("PT: %s\n", best_pt);
    return 0;
}

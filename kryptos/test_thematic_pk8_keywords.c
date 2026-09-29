#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

#define N 153

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static float qtable[26][26][26][26];
static char valid_q[26][26][26][26];

static void load_quads(void) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    qtable[a][b][c][d] = -9.5f;
                    valid_q[a][b][c][d] = 0;
                }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) return;
    char buf[64];
    while (fgets(buf, sizeof(buf), f)) {
        char q[5]; float sc;
        if (sscanf(buf, "%4s %f", q, &sc) == 2) {
            int a = q[0] - 'A', b = q[1] - 'A', c = q[2] - 'A', d = q[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                qtable[a][b][c][d] = sc;
                valid_q[a][b][c][d] = 1;
            }
        }
    }
    fclose(f);
}

static inline float eval_pt_fast(const char *pt, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int i = 0; i < N - 3; i++) {
        int a = pt[i] - 'A', b = pt[i+1] - 'A', c = pt[i+2] - 'A', d = pt[i+3] - 'A';
        sc += qtable[a][b][c][d];
        if (!valid_q[a][b][c][d]) def++;
    }
    *out_def = def;
    return sc / (float)(N - 3);
}

int main(void) {
    load_quads();

    const char *w4_list[] = {
        "BERN", "EAST", "KNOT", "NEED", "IRON", "WIRE", "FIRE", "GOLD", "FLAX", "LARD",
        "COAL", "HEAT", "ANVL", "TONG", "FILE", "SEAR", "FURL", "WEAV", "CORE", "PULL",
        "GRID", "WALL", "SHOP", "DAYS", "WORK", "FINE", "EDGE", "HEAD", "BLOW", "MAKE",
        "STUD", "TAKE", "TIME", "NINE", "TENX", "GLOW", "HELD", "WARM", "HOUR", "HAND",
        "TRUE", "DEEP", "LEAD", "ROD", "EYES", "ROAR", "SOOT", "BEAT", "COOL", "BOND"
    };
    int n4 = sizeof(w4_list) / sizeof(w4_list[0]);

    const char *w5_list[] = {
        "CLOCK", "STEEL", "FLAME", "ANVIL", "HEATH", "TONGS", "FLAWS", "STUDY", "YEARS",
        "LIGHT", "SHADE", "WEAVE", "FIBER", "POINT", "SHAPE", "FORGE", "SMOKE", "WHITE",
        "HEART", "HEARTH", "BLOWS", "DRAWN", "PIECE", "LABOR", "LABOUR", "NEEDL", "PUNCH",
        "KNIFE", "BRASS", "WATER", "CRAFT", "SKILL", "FLUID", "FROST", "CHILL", "SPARK",
        "CLEAN", "SHARP", "BLUNT", "SOLID", "HEAVY", "ROUND", "SPLIT", "GLASS", "BERNE",
        "TIGHT", "KNOTS", "ROADS", "TRACK", "ROUTE"
    };
    int n5 = sizeof(w5_list) / sizeof(w5_list[0]);

    const char *w6_list[] = {
        "BERLIN", "NEEDLE", "THREAD", "BELLOW", "HEARTH", "PURIFY", "TEMPER", "FORGED",
        "SILVER", "COPPER", "FLOWER", "STRAND", "SECTION", "LENGTH", "EXPAND", "SPRING",
        "GUTTER", "HAMMER", "LABOUR", "COARSE", "SMOOTH", "CHISEL", "PIERCE", "STRIKE",
        "CRUCIB", "ANNEAL", "METALS", "HARDEN", "SOFTEN", "MASTER", "APPREN", "WORKER",
        "FLIGHT", "KRYPTO", "SANBOR", "SCHEID", "MAKERS", "WEAPON", "SPLINT", "BLADES",
        "POWDER", "CINDER", "FLAMES", "BELLOW", "TONGSX", "FURNAC", "SOCKET", "HANDLE"
    };
    int n6 = sizeof(w6_list) / sizeof(w6_list[0]);

    const char *w7_list[] = {
        "KRYPTOS", "SANBORN", "SCHEIDT", "WEBSTER", "BERLINC", "DEFUNCT", "ARCHIVE",
        "PELLEGR", "FLORENC", "TEXTILE", "FURLONG", "TENSION", "FIBRESX", "COMPLEX",
        "SURGICA", "ANATOMI", "DEMONST", "CORRESP", "PRECISI", "DISTORT", "INTERLO",
        "COORDEN", "WHITESM", "WORKSHO", "EXQUISI", "PRACTIC", "PROPERX", "BELLOWS",
        "TEMPERI", "PURIFIED", "ANVILST", "DRAWPLA", "NEEDLES", "THREADS", "STRIKES",
        "HAMMERS", "METALLI", "CHISELS", "PIERCED", "SMELTER", "FURNACE", "CRUCIBL"
    };
    int n7 = sizeof(w7_list) / sizeof(w7_list[0]);

    printf("======================================================================\n");
    printf("EVALUATING THEMATIC 4-WORD COMBINATIONS ON PK8: %d x %d x %d x %d = %lld\n",
           n4, n5, n6, n7, (long long)n4 * n5 * n6 * n7);
    printf("======================================================================\n");

    int ct_kr[N];
    for (int i = 0; i < N; i++) ct_kr[i] = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;

    float best_sc = -999.0f;
    int best_def = 999;
    char best_w4[16], best_w5[16], best_w6[16], best_w7[16];

    #pragma omp parallel
    {
        float loc_best_sc = -999.0f;
        int loc_best_def = 999;
        char loc_w4[16], loc_w5[16], loc_w6[16], loc_w7[16];

        #pragma omp for collapse(2) schedule(dynamic)
        for (int i4 = 0; i4 < n4; i4++) {
            for (int i5 = 0; i5 < n5; i5++) {
                int q4[4], q5[5];
                for (int k = 0; k < 4; k++) q4[k] = strchr(KRYPTOS, w4_list[i4][k]) - KRYPTOS;
                for (int k = 0; k < 5; k++) q5[k] = strchr(KRYPTOS, w5_list[i5][k]) - KRYPTOS;

                for (int i6 = 0; i6 < n6; i6++) {
                    int q6[6];
                    for (int k = 0; k < 6; k++) q6[k] = strchr(KRYPTOS, w6_list[i6][k]) - KRYPTOS;

                    for (int i7 = 0; i7 < n7; i7++) {
                        int q7[7];
                        for (int k = 0; k < 7; k++) q7[k] = strchr(KRYPTOS, w7_list[i7][k]) - KRYPTOS;

                        char pt[N + 1];
                        for (int i = 0; i < N; i++) {
                            int shift = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                            int p_idx = (ct_kr[i] - shift + 26) % 26;
                            pt[i] = KRYPTOS[p_idx];
                        }
                        pt[N] = '\0';

                        int def;
                        float sc = eval_pt_fast(pt, &def);
                        if (def < loc_best_def || (def == loc_best_def && sc > loc_best_sc)) {
                            loc_best_def = def;
                            loc_best_sc = sc;
                            strcpy(loc_w4, w4_list[i4]);
                            strcpy(loc_w5, w5_list[i5]);
                            strcpy(loc_w6, w6_list[i6]);
                            strcpy(loc_w7, w7_list[i7]);
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best_def < best_def || (loc_best_def == best_def && loc_best_sc > best_sc)) {
                best_def = loc_best_def;
                best_sc = loc_best_sc;
                strcpy(best_w4, loc_w4);
                strcpy(best_w5, loc_w5);
                strcpy(best_w6, loc_w6);
                strcpy(best_w7, loc_w7);
                printf("  New Best: W4=%s, W5=%s, W6=%s, W7=%s | Score = %.4f | Defects = %d / 150 (%.1f%% valid)\n",
                       best_w4, best_w5, best_w6, best_w7, best_sc, best_def, (150 - best_def)/150.0f * 100.0f);
            }
        }
    }

    printf("\n======================================================\n");
    printf("FINAL THEMATIC 4-WORD SWEEP RESULT:\n");
    printf("Best Combination: W4=%s, W5=%s, W6=%s, W7=%s\n", best_w4, best_w5, best_w6, best_w7);
    printf("Score: %.4f | Defects: %d / 150 (%.1f%% valid)\n",
           best_sc, best_def, (150 - best_def)/150.0f * 100.0f);

    // Decrypt and print sample
    int q4[4], q5[5], q6[6], q7[7];
    for (int k = 0; k < 4; k++) q4[k] = strchr(KRYPTOS, best_w4[k]) - KRYPTOS;
    for (int k = 0; k < 5; k++) q5[k] = strchr(KRYPTOS, best_w5[k]) - KRYPTOS;
    for (int k = 0; k < 6; k++) q6[k] = strchr(KRYPTOS, best_w6[k]) - KRYPTOS;
    for (int k = 0; k < 7; k++) q7[k] = strchr(KRYPTOS, best_w7[k]) - KRYPTOS;
    char pt[N + 1];
    for (int i = 0; i < N; i++) {
        int shift = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
        int p_idx = (ct_kr[i] - shift + 26) % 26;
        pt[i] = KRYPTOS[p_idx];
    }
    pt[N] = '\0';
    printf("Plaintext Sample: %s\n", pt);

    return 0;
}

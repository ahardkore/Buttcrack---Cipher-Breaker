#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static float quadgrams[26][26][26][26];

void load_quads() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    quadgrams[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    char line[64];
    double total = 5348433.0;
    while (fgets(line, sizeof(line), f)) {
        char g[5]; double cnt;
        if (sscanf(line, "%4s %lf", g, &cnt) == 2) {
            int a = g[0]-'A', b = g[1]-'A', c = g[2]-'A', d = g[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quadgrams[a][b][c][d] = (float)log10(cnt / total);
            }
        }
    }
    fclose(f);
}

static inline float eval_state(const int *ct_k, const int *q4, const int *q5, const int *q6, const int *q7, int *pt_out) {
    float sc = 0;
    int prev0, prev1, prev2, prev3;
    for (int i = 0; i < N; i++) {
        int shift = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
        int z_kr = (ct_k[i] - shift + 26) % 26;
        char ch = ALPH[z_kr];
        int cur = ch - 'A';
        if (pt_out) pt_out[i] = cur;

        if (i == 0) prev0 = cur;
        else if (i == 1) prev1 = cur;
        else if (i == 2) prev2 = cur;
        else {
            prev3 = cur;
            sc += quadgrams[prev0][prev1][prev2][prev3];
            prev0 = prev1; prev1 = prev2; prev2 = prev3;
        }
    }
    return sc / (N - 3);
}

// Thematic words
static const char *words4[] = {
    "IRON", "GOLD", "LEAD", "TOOL", "WORK", "BLOW", "COAL", "HEAT", "FIRE",
    "MELT", "CAST", "FILE", "WIRE", "BOND", "HORN", "FLUX", "CLAY", "FORM",
    "LINE", "DRAW", "BEAT", "HARD", "SOFT", "PURE", "FINE", "TRUE", "MARK",
    "SEAL", "KNOT", "LOCK", "GATE", "WALL", "ROOF", "DOOR", "BASE", "EDGE",
    "RING", "STUD", "COIN", "NAIL", "WOOD", "PALE", "RUST", "GRAY", "ROSE",
    "DARK", "COLD", "WARM", "DUST", "ASHY", "TINM", "ZINC", "BRON"
};

static const char *words5[] = {
    "ANVIL", "FORGE", "STEEL", "BRASS", "TONGS", "SMELT", "FLAME", "SHEAR",
    "PLATE", "STAND", "BENCH", "METAL", "CRAFT", "TRACE", "MODEL", "SHAPE",
    "POINT", "ANGLE", "ORDER", "STONE", "COLOR", "PAINT", "PANEL", "LIGHT",
    "SHADE", "SCULP", "PILOT", "GUIDE", "TORCH", "WATER", "EARTH", "PULSE",
    "CYCLE", "CLOCK", "TIMER", "SCALE", "RATIO", "PIECE", "SHEET", "STRIP",
    "LAYER", "GRAIN", "TEMPR", "CHISE", "HAMMR", "ALLOY", "INGOT", "MOUND",
    "BEVEL", "SHANK", "POINT", "RIDGE", "BLOCK", "FRAME", "GROOV", "PUNCH"
};

static const char *words6[] = {
    "HEARTH", "HAMMER", "SILVER", "COPPER", "BRONZE", "SOLDER", "NIELLO",
    "ENAMEL", "ANNEAL", "MALLET", "PINCER", "PLIERS", "CHISEL", "MASTER",
    "TEMPER", "PORTAL", "PENCIL", "GRAVER", "BURINS", "BELLOW", "CRAFTY",
    "WORKER", "SMITHY", "FORGER", "CASTLE", "CHURCH", "TEMPLE", "PALACE",
    "WINDOW", "PILLAR", "COLUMN", "MOSAIC", "FRESCO", "RELIEF", "CARVER",
    "MEDALS", "PLATED", "ENGRAV", "POLISH", "SMOOTH", "SHARPN", "YELLOW",
    "GOLDEN", "SPRING", "SUMMER", "AUTUMN", "WINTER", "SHADOW", "FLAKES"
};

static const char *words7[] = {
    "BELLOWS", "FURNACE", "DRAWING", "BEATING", "CHASING", "BURNISH",
    "GILDING", "STUDENT", "SCHOLAR", "WORKMAN", "MELTING", "CASTING",
    "SOLDERS", "ENAMELS", "NIELLOS", "CARVING", "SHAPING", "JOINING",
    "FITTING", "SETTING", "RESTORE", "HANDLES", "PINCERS", "CHISELS",
    "ANVILS", "HAMMERS", "METALS", "WHITE", "PATTERN", "DESIGNS",
    "FIGURES", "STATUES", "PRACTIC", "STUDIED", "LEARNED", "TAUGHT",
    "MASTERS", "TUTORED", "CREATED", "FORGING", "TEMPERS", "ANNEALS",
    "ENGRAVE", "KRYPTOS", "SCULPTU", "SANCTUM", "CLOSTER", "ABBEYS",
    "CHURCHS", "CATHEDR"
};

int main() {
    load_quads();

    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int ct_k[N];
    for (int i=0; i<N; i++) ct_k[i] = k2i[(int)CT[i]];

    int n4 = sizeof(words4) / sizeof(words4[0]);
    int n5 = sizeof(words5) / sizeof(words5[0]);
    int n6 = sizeof(words6) / sizeof(words6[0]);
    int n7 = sizeof(words7) / sizeof(words7[0]);

    printf("Sweeping thematic combinations: %d x %d x %d x %d = %ld combinations\n",
           n4, n5, n6, n7, (long)n4 * n5 * n6 * n7);

    float global_best_sc = -1e9f;
    char global_best_w4[8], global_best_w5[8], global_best_w6[8], global_best_w7[8];
    char global_best_pt[N+1];

    #pragma omp parallel
    {
        float local_best_sc = -1e9f;
        char local_best_w4[8], local_best_w5[8], local_best_w6[8], local_best_w7[8];
        char local_best_pt[N+1];

        #pragma omp for collapse(2) schedule(dynamic, 1)
        for (int i4 = 0; i4 < n4; i4++) {
            for (int i5 = 0; i5 < n5; i5++) {
                int q4[4], q5[5];
                for (int k=0; k<4; k++) q4[k] = k2i[(int)words4[i4][k]];
                for (int k=0; k<5; k++) q5[k] = k2i[(int)words5[i5][k]];

                for (int i6 = 0; i6 < n6; i6++) {
                    int q6[6];
                    for (int k=0; k<6; k++) q6[k] = k2i[(int)words6[i6][k]];

                    for (int i7 = 0; i7 < n7; i7++) {
                        int q7[7];
                        for (int k=0; k<7; k++) q7[k] = k2i[(int)words7[i7][k]];

                        int pt[N];
                        float sc = eval_state(ct_k, q4, q5, q6, q7, pt);

                        if (sc > local_best_sc) {
                            local_best_sc = sc;
                            strcpy(local_best_w4, words4[i4]);
                            strcpy(local_best_w5, words5[i5]);
                            strcpy(local_best_w6, words6[i6]);
                            strcpy(local_best_w7, words7[i7]);
                            for (int m=0; m<N; m++) local_best_pt[m] = pt[m] + 'A';
                            local_best_pt[N] = 0;
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(global_best_w4, local_best_w4);
                strcpy(global_best_w5, local_best_w5);
                strcpy(global_best_w6, local_best_w6);
                strcpy(global_best_w7, local_best_w7);
                strcpy(global_best_pt, local_best_pt);
            }
        }
    }

    printf("\nFinished! Global Best Score: %.4f\n", global_best_sc);
    printf("W4: %s | W5: %s | W6: %s | W7: %s\n",
           global_best_w4, global_best_w5, global_best_w6, global_best_w7);
    printf("Plaintext:\n%s\n", global_best_pt);

    return 0;
}

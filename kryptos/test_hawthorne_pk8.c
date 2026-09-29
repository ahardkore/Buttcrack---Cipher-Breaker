#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static float quad[26][26][26][26];

void load_quadgrams() {
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Failed to open english_quadgrams.txt\n"); exit(1); }
    char line[128];
    double total = 0;
    static double counts[26][26][26][26];
    memset(counts, 0, sizeof(counts));
    while (fgets(line, sizeof(line), f)) {
        char gram[5]; double count;
        if (sscanf(line, "%4s %lf", gram, &count) == 2) {
            int a = gram[0] - 'A', b = gram[1] - 'A', c = gram[2] - 'A', d = gram[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                counts[a][b][c][d] = count;
                total += count;
            }
        }
    }
    fclose(f);
    float floor_val = log10f(0.01f / total);
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = counts[a][b][c][d] > 0 ? log10f(counts[a][b][c][d] / total) : floor_val;
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const char *words4[] = {
    "DRAW", "WIRE", "IRON", "GOLD", "FIRE", "HEAT", "TOOL", "FLAT", "FOOT", "GLUE",
    "KNOP", "LEAD", "MOLD", "PIPE", "ROBE", "THIN", "WIND", "WOOD", "SEAT", "WALL",
    "CLAY", "SALT", "LEES", "HEAD", "RAMS", "BLOW", "COAL", "WARM", "COLD", "BURN",
    "POUR", "CAST", "FORM", "BEAT", "FILL", "RING", "SPUR", "ZINC", "FLUX", "EAST",
    "TIME", "HOUR", "DIAL", "ROSE"
};
static int n4 = sizeof(words4) / sizeof(words4[0]);

static const char *words5[] = {
    "ROGER", "TONGS", "FORGE", "ANVIL", "COALS", "STEEL", "ALLOY", "BRASS", "CLOTH",
    "COLOR", "CRUET", "DRIED", "GREEN", "GRIND", "OCHER", "OXIDE", "PAINT", "PUNCH",
    "RESIN", "ROBES", "ROUND", "SHAPE", "SHEET", "SMEAR", "STICK", "STONE", "THICK",
    "THIRD", "WIDTH", "WHITE", "BLACK", "SMITH", "WIRES", "DRAWN", "HOLES", "HEATS",
    "NAILS", "FILES", "MOULD", "MOLDS", "METAL", "RIVET", "BLADE", "KNIFE", "GRAVE",
    "TABLE", "BENCH", "BEATS", "NORTH", "CLOCK", "LUCID"
};
static int n5 = sizeof(words5) / sizeof(words5[0]);

static const char *words6[] = {
    "HAMMER", "COPPER", "SILVER", "NIELLO", "SMOOTH", "SOLDER", "MELTED", "ANNEAL",
    "CENSER", "CERUSE", "ENAMEL", "EVENLY", "FOLIUM", "GROOVE", "HANDLE", "INSIDE",
    "MINIUM", "POLISH", "POWDER", "REDHOT", "SCRAPE", "VESSEL", "WOODEN", "BELLOW",
    "HEARTH", "QUENCH", "TEMPER", "MOLTEN", "FORGED", "SPARKS", "ANVILS", "PINCER",
    "PLIERS", "RANGES", "CHALIC", "SOCKET", "PUNCHS", "BORDER", "WINDOW", "TRENCH",
    "FLUXES", "PLATES", "BERLIN", "SHADOW"
};
static int n6 = sizeof(words6) / sizeof(words6[0]);

static const char *words7[] = {
    "BELLOWS", "CHALICE", "FURNACE", "SLENDER", "RUNCINA", "CHARCOA", "ENGRAVE",
    "PIGMENT", "SPANISH", "THICKER", "HAMMERS", "PINCERS", "FORCEPS", "TEMPERS",
    "HEARTHS", "FLATTEN", "HOLLOWS", "ANNEALS", "NEEDLES", "ARTISAN", "MELTING",
    "CASTING", "LETTERS", "DRAWING", "WORKMEN", "INGOTED", "CRUCIBL", "KRYPTOS",
    "SANBORN", "LANGLEY", "COMPASS", "DIGETAL"
};
static int n7 = sizeof(words7) / sizeof(words7[0]);

int main() {
    load_quadgrams();
    int N = strlen(PK8_CT);
    printf("Testing Hawthorne terms on PK8: %d x %d x %d x %d = %d configs\n",
           n4, n5, n6, n7, n4 * n5 * n6 * n7);

    for (int model = 0; model < 4; model++) {
        const char *alpha = (model < 2) ? KRYPTOS : STD;
        int is_beau = (model % 2 == 1);
        const char *mname = (model < 2) ? "KRYPTOS" : "STD";
        const char *mode = is_beau ? "Beaufort" : "Vigenere";

        int c_idx[153];
        int alpha_to_std[26];
        for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
        for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK8_CT[i]) - alpha;

        int i4[100][4], i5[100][5], i6[100][6], i7[100][7];
        for (int i = 0; i < n4; i++) for (int j = 0; j < 4; j++) i4[i][j] = strchr(alpha, words4[i][j]) - alpha;
        for (int i = 0; i < n5; i++) for (int j = 0; j < 5; j++) i5[i][j] = strchr(alpha, words5[i][j]) - alpha;
        for (int i = 0; i < n6; i++) for (int j = 0; j < 6; j++) i6[i][j] = strchr(alpha, words6[i][j]) - alpha;
        for (int i = 0; i < n7; i++) for (int j = 0; j < 7; j++) i7[i][j] = strchr(alpha, words7[i][j]) - alpha;

        for (int a = 0; a < n4; a++) {
            for (int b = 0; b < n5; b++) {
                int kAB[153];
                for (int j = 0; j < N; j++) kAB[j] = (i4[a][j % 4] + i5[b][j % 5]) % 26;

                for (int c = 0; c < n6; c++) {
                    int kABC[153];
                    for (int j = 0; j < N; j++) kABC[j] = (kAB[j] + i6[c][j % 6]) % 26;

                    for (int d = 0; d < n7; d++) {
                        int pt[153];
                        for (int j = 0; j < 16; j++) {
                            int k = (kABC[j] + i7[d][j % 7]) % 26;
                            int p = is_beau ? ((k - c_idx[j] + 26) % 26) : ((c_idx[j] - k + 26) % 26);
                            pt[j] = alpha_to_std[p];
                        }
                        float sc_early = 0;
                        for (int j = 0; j < 13; j++) sc_early += quad[pt[j]][pt[j+1]][pt[j+2]][pt[j+3]];
                        if (sc_early < -70.0f) continue;

                        for (int j = 16; j < N; j++) {
                            int k = (kABC[j] + i7[d][j % 7]) % 26;
                            int p = is_beau ? ((k - c_idx[j] + 26) % 26) : ((c_idx[j] - k + 26) % 26);
                            pt[j] = alpha_to_std[p];
                        }
                        float sc = 0;
                        for (int j = 0; j < N - 3; j++) sc += quad[pt[j]][pt[j+1]][pt[j+2]][pt[j+3]];
                        sc /= (N - 3);

                        if (sc > -5.2f) {
                            printf("HIT! [%s %s] (%s,%s,%s,%s) sc=%6.4f | ",
                                   mname, mode, words4[a], words5[b], words6[c], words7[d], sc);
                            for (int j = 0; j < 50; j++) printf("%c", 'A' + pt[j]);
                            printf("\n");
                        }
                    }
                }
            }
        }
    }
    printf("Test complete!\n");
    return 0;
}

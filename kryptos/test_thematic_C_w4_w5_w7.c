#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *CT9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static int C[144];
static const int N = 144;

typedef struct {
    char word[8];
    int shifts[7];
} Word;

static Word *w7_list = NULL;
static int n7 = 0;

static const char *w4_thematic[] = {
    "EAST", "WEST", "SLOW", "TOMB", "GOLD", "MINE", "CAMP", "DOOR", "HEAD", "WALL",
    "HAND", "TREE", "BEAM", "RAYS", "LINE", "GRID", "CODE", "SEAL", "TIME", "TRUE",
    "NOTE", "CLUE", "NODE", "KNOT", "POLE", "IRON", "WIRE", "FIRE", "COAL", "HEAT",
    "ANNE", "FORG", "CAST", "BLOW", "LEAD", "TOOL", "BEAT", "LENS", "RODS", "SHOE",
    "WORK", "WOOD", "DIAL", "HOUR", "ZERO", "PURE", "PULL", "BORE", "FILE", "DRAW"
};
static const int n4 = sizeof(w4_thematic)/sizeof(w4_thematic[0]);

static const char *w5_thematic[] = {
    "CLOCK", "SHIPS", "NORTH", "SOUTH", "LIGHT", "SHADE", "FIELD", "EARTH", "DEBRI",
    "CANDL", "ANVIL", "STEEL", "FLAME", "TONGS", "HEART", "FORGE", "WATER", "SMOKE",
    "BLACK", "WHITE", "BRASS", "POINT", "SHARP", "TAPER", "METAL", "CHISE", "BERLN",
    "MEDOW", "RADII", "ABSCI", "SCALE", "STONE", "GAUGE", "PLIERS", "TWIST", "FRAME",
    "LAYER", "CRAFT", "TIGHT", "KNOTS", "ROUND", "PLATE", "DRIFT", "POUND", "SMELT"
};
static const int n5 = sizeof(w5_thematic)/sizeof(w5_thematic[0]);

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
        C[i] = std_to_k[CT9_REAL[i] - 'A'];
    }

    w7_list = malloc(50000 * sizeof(Word));
    f = fopen("words_alpha.txt", "r");
    if (!f) { fprintf(stderr, "Cannot open words_alpha.txt\n"); exit(1); }
    char buf[64];
    while (fscanf(f, "%63s", buf) == 1) {
        if (strlen(buf) == 7) {
            int ok = 1;
            for (int i = 0; i < 7; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(w7_list[n7].word, buf);
            for (int i = 0; i < 7; i++) w7_list[n7].shifts[i] = std_to_k[buf[i] - 'A'];
            n7++;
        }
    }
    fclose(f);
    printf("Loaded: W4_them=%d, W5_them=%d, W7_all=%d\n", n4, n5, n7);
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    init();

    int s4[n4][4], s5[n5][5];
    for (int i = 0; i < n4; i++) for (int j = 0; j < 4; j++) s4[i][j] = std_to_k[w4_thematic[i][j] - 'A'];
    for (int i = 0; i < n5; i++) for (int j = 0; j < 5; j++) s5[i][j] = std_to_k[w5_thematic[i][j] - 'A'];

    printf("Sweeping (W4, W5, W7) on RAW C with rotations: %d W4 x %d W5 x 20 rot x %d W7 = %lld combos...\n",
           n4, n5, n7, (long long)n4 * n5 * 20 * n7);

    float best_sc = -999.0f;
    char best_hit[64] = "";
    char best_pt[150] = "";

    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_hit[64] = "";
        char local_pt[150] = "";

        #pragma omp for schedule(dynamic, 1)
        for (int i4 = 0; i4 < n4; i4++) {
            for (int i5 = 0; i5 < n5; i5++) {
                for (int r4 = 0; r4 < 4; r4++) {
                    for (int r5 = 0; r5 < 5; r5++) {
                        // Precompute intermediate stream C_prime = C - s4 - s5
                        int C_prime[144];
                        for (int i = 0; i < 144; i++) {
                            int k = s4[i4][(i + r4) & 3] + s5[i5][(i + r5) % 5];
                            C_prime[i] = (C[i] - k + 52) % 26;
                        }

                        // Test all 41,998 W7
                        for (int i7 = 0; i7 < n7; i7++) {
                            const int *s7 = w7_list[i7].shifts;

                            // Fast gate: first 16 chars
                            int pt[16];
                            for (int i = 0; i < 16; i++) {
                                int p_idx = (C_prime[i] - s7[i % 7] + 26) % 26;
                                pt[i] = k_to_std[p_idx];
                            }
                            float sc = 0.0f;
                            for (int i = 0; i < 13; i++) sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                            sc /= 13.0f;
                            if (sc < -5.6f) continue;

                            int full_pt[144];
                            for (int i = 0; i < 16; i++) full_pt[i] = pt[i];
                            for (int i = 16; i < 144; i++) {
                                int p_idx = (C_prime[i] - s7[i % 7] + 26) % 26;
                                full_pt[i] = k_to_std[p_idx];
                            }
                            float full_sc = sc * 13.0f;
                            for (int i = 13; i < 141; i++) full_sc += quad_table[full_pt[i]][full_pt[i+1]][full_pt[i+2]][full_pt[i+3]];
                            full_sc /= 141.0f;

                            if (full_sc > local_best) {
                                local_best = full_sc;
                                sprintf(local_hit, "%s(r%d)+%s(r%d)+%s",
                                        w4_thematic[i4], r4, w5_thematic[i5], r5, w7_list[i7].word);
                                for (int i = 0; i < 144; i++) local_pt[i] = full_pt[i] + 'A';
                                local_pt[144] = '\0';
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best > best_sc) {
                best_sc = local_best;
                strcpy(best_hit, local_hit);
                strcpy(best_pt, local_pt);
                printf("New best: sc=%.3f | %s\nPT: %.55s...\n", best_sc, best_hit, best_pt);
                fflush(stdout);
            }
        }
    }

    printf("\nFinished sweep on RAW C. Global best: sc=%.3f (%s)\nPT: %s\n",
           best_sc, best_hit, best_pt);
    return 0;
}

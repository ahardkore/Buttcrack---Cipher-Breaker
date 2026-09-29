#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static const char *CT9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *ALPH_S = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

static int k_to_std[26];
static int std_to_k[26];

// Quadgram loading
void load_quads() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.0f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) {
        // try alternative format
        f = fopen("english_quadgrams.txt", "r");
    }
    if (!f) {
        printf("Error: quadgram file not found!\n");
        exit(1);
    }
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
}

// Fast scoring in standard alphabet (0-25)
static inline float score_text(const int *text, int len) {
    float s = 0.0f;
    for (int i = 0; i < len - 3; i++) {
        s += quad_table[text[i]][text[i+1]][text[i+2]][text[i+3]];
    }
    return s / (len - 3);
}

// Global best tracker
static float global_best_score = -999.0f;
static char global_best_pt[150] = "";
static char global_best_desc[256] = "";

void record_hit(float sc, const int *pt, int len, const char *desc) {
    #pragma omp critical
    {
        if (sc > global_best_score) {
            global_best_score = sc;
            for (int i = 0; i < len; i++) global_best_pt[i] = 'A' + pt[i];
            global_best_pt[len] = '\0';
            strncpy(global_best_desc, desc, 255);
            printf("\n[NEW BEST] Score: %.4f | %s\nPT: %.70s...\n", sc, desc, global_best_pt);
            fflush(stdout);
        }
    }
}

// All keywords from K1-8
static const char *KEYWORDS[] = {
    // PK1
    "PROVENANCE", "ARCHIVE", "PELLEGRIN", "ARCHIVISTS", "TWELVE", "EIGHT",
    // PK2
    "MARGINS", "MARGINALIA", "NEEDLE", "TEXTILES", "TREATISE", "SEVEN",
    "UNAGOTANTOSOTTILEDALEGGEREQUALUNQUENODO",
    // PK3
    "PENTIMENTO", "ORDINATE", "BERN", "ANATOMIST", "SURGICAL", "VIENNESE", "FIFTEEN", "SIX",
    // PK4
    "FURLONGS",
    // PK5
    "FIBERS", "LENS",
    // PK6
    "PORTAL", "WHITESMITH", "WORKSHOP", "TOOLS", "GUTTER", "RESIDUE", "PRACTICE", "MAKING", "TEN",
    // PK7
    "HEARTH", "BELLOWS", "COALS", "FIRE", "HEAT", "WHITE",
    // K1-K4 (Sanborn)
    "KRYPTOS", "PALIMPSEST", "ABSCISSA", "BERLIN", "CLOCK", "EAST", "NORTHEAST",
    // Pellegrin 1530 Title
    "LAFLEURDELASCIENCEDEPOURTRAICTURE", "PATRONSDEBRODERIE", "MORESQUES",
    // Artisan actions
    "ANVIL", "HAMMER", "CRUCIBLE", "FURNACE", "TEMPER", "ANNEAL", "CHISEL",
    "SILVER", "GOLD", "WIRE", "DRAWPLATE", "PUNCHED", "TONGS", "INGOT", "BILLET", "SWAGING"
};
static const int NUM_KEYWORDS = sizeof(KEYWORDS) / sizeof(KEYWORDS[0]);

int main() {
    load_quads();
    printf("Master K1-8 Combinatorial Engine initialized.\n");
    printf("Evaluating on %d keywords from K1-K8...\n", NUM_KEYWORDS);

    int C_k[N], C_s[N];
    for (int i = 0; i < N; i++) {
        C_s[i] = CT9_RAW[i] - 'A';
        C_k[i] = std_to_k[C_s[i]];
    }

    // PHASE 1: Direct Single & Dual Keyword Substitutions (Quag3, Vig, Beau)
    printf("\n=== Phase 1: Dual-Keyword Sum-Clocks (K1-8 pairs) ===\n");
    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < NUM_KEYWORDS; i++) {
        const char *k1 = KEYWORDS[i];
        int l1 = strlen(k1);
        int pt_std[N];

        for (int j = 0; j < NUM_KEYWORDS; j++) {
            const char *k2 = KEYWORDS[j];
            int l2 = strlen(k2);

            // Test across phase offsets
            for (int offset = 0; offset < l2; offset++) {
                // Mode 1: KRYPTOS Vigenere (Quag3 sum-clock)
                for (int m = 0; m < N; m++) {
                    int s1 = std_to_k[k1[m % l1] - 'A'];
                    int s2 = std_to_k[k2[(m + offset) % l2] - 'A'];
                    int shift = (s1 + s2) % 26;
                    int p_k = (C_k[m] - shift + 26) % 26;
                    pt_std[m] = k_to_std[p_k];
                }
                float sc = score_text(pt_std, N);
                if (sc > -7.6f) {
                    char desc[256];
                    snprintf(desc, sizeof(desc), "Quag3: %s + %s(off=%d)", k1, k2, offset);
                    record_hit(sc, pt_std, N, desc);
                }

                // Mode 2: STANDARD Vigenere sum-clock
                for (int m = 0; m < N; m++) {
                    int s1 = k1[m % l1] - 'A';
                    int s2 = k2[(m + offset) % l2] - 'A';
                    int shift = (s1 + s2) % 26;
                    pt_std[m] = (C_s[m] - shift + 26) % 26;
                }
                sc = score_text(pt_std, N);
                if (sc > -7.6f) {
                    char desc[256];
                    snprintf(desc, sizeof(desc), "STD-Vig: %s + %s(off=%d)", k1, k2, offset);
                    record_hit(sc, pt_std, N, desc);
                }

                // Mode 3: KRYPTOS Beaufort sum-clock
                for (int m = 0; m < N; m++) {
                    int s1 = std_to_k[k1[m % l1] - 'A'];
                    int s2 = std_to_k[k2[(m + offset) % l2] - 'A'];
                    int shift = (s1 + s2) % 26;
                    int p_k = (shift - C_k[m] + 26) % 26;
                    pt_std[m] = k_to_std[p_k];
                }
                sc = score_text(pt_std, N);
                if (sc > -7.6f) {
                    char desc[256];
                    snprintf(desc, sizeof(desc), "Quag3-Beaufort: %s + %s(off=%d)", k1, k2, offset);
                    record_hit(sc, pt_std, N, desc);
                }
            }
        }
    }

    printf("Phase 1 complete. Best score: %.4f\n", global_best_score);
    return 0;
}

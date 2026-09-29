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

void load_quads() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.0f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Error: quadgram file not found!\n"); exit(1); }
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

static inline float score_text(const int *text, int len) {
    float s = 0.0f;
    for (int i = 0; i < len - 3; i++) {
        s += quad_table[text[i]][text[i+1]][text[i+2]][text[i+3]];
    }
    return s / (len - 3);
}

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

static const char *KEYWORDS[] = {
    "PROVENANCE", "ARCHIVE", "PELLEGRIN", "ARCHIVISTS", "TWELVE", "EIGHT",
    "MARGINS", "MARGINALIA", "NEEDLE", "TEXTILES", "TREATISE", "SEVEN",
    "UNAGOTANTOSOTTILEDALEGGEREQUALUNQUENODO",
    "PENTIMENTO", "ORDINATE", "BERN", "ANATOMIST", "SURGICAL", "VIENNESE", "FIFTEEN", "SIX",
    "FURLONGS", "FIBERS", "LENS", "PORTAL", "WHITESMITH", "WORKSHOP", "TOOLS",
    "GUTTER", "RESIDUE", "PRACTICE", "MAKING", "TEN", "HEARTH", "BELLOWS", "COALS",
    "FIRE", "HEAT", "WHITE", "KRYPTOS", "PALIMPSEST", "ABSCISSA", "BERLIN",
    "CLOCK", "EAST", "NORTHEAST", "LAFLEURDELASCIENCEDEPOURTRAICTURE", "PATRONSDEBRODERIE",
    "MORESQUES", "ANVIL", "HAMMER", "CRUCIBLE", "FURNACE", "TEMPER", "ANNEAL",
    "CHISEL", "SILVER", "GOLD", "WIRE", "DRAWPLATE", "PUNCHED", "TONGS", "INGOT", "BILLET", "SWAGING"
};
static const int NUM_KEYWORDS = sizeof(KEYWORDS) / sizeof(KEYWORDS[0]);

// Permutation of a keyword
void keyword_to_order(const char *kw, int *order, int len) {
    int sorted_idx[len];
    for (int i = 0; i < len; i++) sorted_idx[i] = i;
    for (int i = 0; i < len - 1; i++) {
        for (int j = i + 1; j < len; j++) {
            if (kw[sorted_idx[j]] < kw[sorted_idx[i]] || 
               (kw[sorted_idx[j]] == kw[sorted_idx[i]] && sorted_idx[j] < sorted_idx[i])) {
                int tmp = sorted_idx[i];
                sorted_idx[i] = sorted_idx[j];
                sorted_idx[j] = tmp;
            }
        }
    }
    for (int i = 0; i < len; i++) order[sorted_idx[i]] = i;
}

// Columnar decode with given width and order
void columnar_decode(const int *in, int *out, int width, const int *order, int unit) {
    int total_units = N / unit;
    int rows = total_units / width;
    for (int col = 0; col < width; col++) {
        int orig_col = order[col];
        for (int r = 0; r < rows; r++) {
            for (int u = 0; u < unit; u++) {
                out[(r * width + orig_col) * unit + u] = in[(col * rows + r) * unit + u];
            }
        }
    }
}

int main() {
    load_quads();
    printf("Master Exhaustive Engine for K1-8 Combinations initialized.\n");

    int C_s[N], C_k[N];
    for (int i = 0; i < N; i++) {
        C_s[i] = CT9_RAW[i] - 'A';
        C_k[i] = std_to_k[C_s[i]];
    }

    // PHASE 1: Single & Dual Keyword Substitutions
    printf("\n--- Running Phase 1: Dual Keyword Sum-Clocks ---\n");
    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < NUM_KEYWORDS; i++) {
        const char *k1 = KEYWORDS[i];
        int l1 = strlen(k1);
        int pt_std[N];

        for (int j = 0; j < NUM_KEYWORDS; j++) {
            const char *k2 = KEYWORDS[j];
            int l2 = strlen(k2);

            for (int offset = 0; offset < l2; offset++) {
                // Quag3
                for (int m = 0; m < N; m++) {
                    int s1 = std_to_k[k1[m % l1] - 'A'];
                    int s2 = std_to_k[k2[(m + offset) % l2] - 'A'];
                    int p_k = (C_k[m] - (s1 + s2) % 26 + 26) % 26;
                    pt_std[m] = k_to_std[p_k];
                }
                float sc = score_text(pt_std, N);
                if (sc > -7.8f) {
                    char desc[256];
                    snprintf(desc, sizeof(desc), "Quag3: %s + %s(off=%d)", k1, k2, offset);
                    record_hit(sc, pt_std, N, desc);
                }

                // STD Vig
                for (int m = 0; m < N; m++) {
                    int s1 = k1[m % l1] - 'A';
                    int s2 = k2[(m + offset) % l2] - 'A';
                    pt_std[m] = (C_s[m] - (s1 + s2) % 26 + 26) % 26;
                }
                sc = score_text(pt_std, N);
                if (sc > -7.8f) {
                    char desc[256];
                    snprintf(desc, sizeof(desc), "STD-Vig: %s + %s(off=%d)", k1, k2, offset);
                    record_hit(sc, pt_std, N, desc);
                }
            }
        }
    }

    // PHASE 2: Transposition OVER Substitution (C -> Transposition -> Substitution -> PT)
    printf("\n--- Running Phase 2: Transposition then Substitution ---\n");
    #pragma omp parallel for schedule(dynamic)
    for (int t = 0; t < NUM_KEYWORDS; t++) {
        const char *tkw = KEYWORDS[t];
        int w = strlen(tkw);
        // Only widths dividing 144
        if (N % w != 0) continue;
        int order[w];
        keyword_to_order(tkw, order, w);

        int trans_s[N], trans_k[N];
        columnar_decode(C_s, trans_s, w, order, 1);
        for (int i = 0; i < N; i++) trans_k[i] = std_to_k[trans_s[i]];

        // Now test all substitution keywords
        for (int s = 0; s < NUM_KEYWORDS; s++) {
            const char *skw = KEYWORDS[s];
            int slen = strlen(skw);
            int pt_std[N];

            // Quag3
            for (int m = 0; m < N; m++) {
                int shift = std_to_k[skw[m % slen] - 'A'];
                int p_k = (trans_k[m] - shift + 26) % 26;
                pt_std[m] = k_to_std[p_k];
            }
            float sc = score_text(pt_std, N);
            if (sc > -7.5f) {
                char desc[256];
                snprintf(desc, sizeof(desc), "Trans(%s, w=%d) -> Quag3(%s)", tkw, w, skw);
                record_hit(sc, pt_std, N, desc);
            }

            // STD Vig
            for (int m = 0; m < N; m++) {
                int shift = skw[m % slen] - 'A';
                pt_std[m] = (trans_s[m] - shift + 26) % 26;
            }
            sc = score_text(pt_std, N);
            if (sc > -7.5f) {
                char desc[256];
                snprintf(desc, sizeof(desc), "Trans(%s, w=%d) -> STD-Vig(%s)", tkw, w, skw);
                record_hit(sc, pt_std, N, desc);
            }
        }
    }

    // PHASE 3: Substitution then Transposition (C -> Substitution -> Transposition -> PT)
    printf("\n--- Running Phase 3: Substitution then Transposition ---\n");
    #pragma omp parallel for schedule(dynamic)
    for (int s = 0; s < NUM_KEYWORDS; s++) {
        const char *skw = KEYWORDS[s];
        int slen = strlen(skw);
        int sub_s[N], sub_k[N];

        // Quag3 peel
        for (int m = 0; m < N; m++) {
            int shift = std_to_k[skw[m % slen] - 'A'];
            int p_k = (C_k[m] - shift + 26) % 26;
            sub_k[m] = k_to_std[p_k];
        }

        // Test all transposition keywords
        for (int t = 0; t < NUM_KEYWORDS; t++) {
            const char *tkw = KEYWORDS[t];
            int w = strlen(tkw);
            if (N % w != 0) continue;
            int order[w];
            keyword_to_order(tkw, order, w);

            int pt_std[N];
            columnar_decode(sub_k, pt_std, w, order, 1);
            float sc = score_text(pt_std, N);
            if (sc > -7.5f) {
                char desc[256];
                snprintf(desc, sizeof(desc), "Quag3(%s) -> Trans(%s, w=%d)", skw, tkw, w);
                record_hit(sc, pt_std, N, desc);
            }
        }
    }

    // PHASE 4: Trigraph Block Transposition (unit=3, w=6) with all K1-8 Keywords
    printf("\n--- Running Phase 4: Trigraph-Block stream (unit=3, w=6) with K1-8 Keywords ---\n");
    int order6[6] = {3, 5, 1, 4, 2, 0};
    int undone_s[N], undone_k[N];
    columnar_decode(C_s, undone_s, 6, order6, 3);
    for (int i = 0; i < N; i++) undone_k[i] = std_to_k[undone_s[i]];

    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < NUM_KEYWORDS; i++) {
        const char *k1 = KEYWORDS[i];
        int l1 = strlen(k1);
        int pt_std[N];

        // Single keyword
        for (int m = 0; m < N; m++) {
            int shift = std_to_k[k1[m % l1] - 'A'];
            int p_k = (undone_k[m] - shift + 26) % 26;
            pt_std[m] = k_to_std[p_k];
        }
        float sc = score_text(pt_std, N);
        if (sc > -7.5f) {
            char desc[256];
            snprintf(desc, sizeof(desc), "Undone(unit=3) -> Quag3(%s)", k1);
            record_hit(sc, pt_std, N, desc);
        }

        // Dual keyword sum-clock on undone
        for (int j = 0; j < NUM_KEYWORDS; j++) {
            const char *k2 = KEYWORDS[j];
            int l2 = strlen(k2);
            for (int offset = 0; offset < l2; offset++) {
                for (int m = 0; m < N; m++) {
                    int s1 = std_to_k[k1[m % l1] - 'A'];
                    int s2 = std_to_k[k2[(m + offset) % l2] - 'A'];
                    int p_k = (undone_k[m] - (s1 + s2) % 26 + 26) % 26;
                    pt_std[m] = k_to_std[p_k];
                }
                sc = score_text(pt_std, N);
                if (sc > -7.5f) {
                    char desc[256];
                    snprintf(desc, sizeof(desc), "Undone(unit=3) -> Quag3: %s + %s(off=%d)", k1, k2, offset);
                    record_hit(sc, pt_std, N, desc);
                }
            }
        }
    }

    printf("\nAll K1-8 combination phases complete!\n");
    printf("Final Global Best Score: %.4f | %s\n", global_best_score, global_best_desc);
    if (global_best_score > -900.0f) {
        printf("Plaintext:\n%s\n", global_best_pt);
    }
    return 0;
}

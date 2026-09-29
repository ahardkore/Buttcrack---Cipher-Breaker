#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 504
#define COLS 42
#define ROWS 12

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const int s28[28] = {
    25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6
};

static const char *pk9_core_pt = "LARDADEFUNCTORDQBOOMRBETHSKWJEREASTYMARINPRAYIALMSOISEARVEMYLAILEBOTHEEDAMESQUNGLAYIMIRLOFATSEREDCISANTIDBYOUSCHESALSOMYRELIFORESSESTIA";

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
    if (!f) { fprintf(stderr, "Missing english_quads.tsv\n"); exit(1); }
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

static inline float get_ioc(const char *txt, int len, int *out_rare) {
    int counts[26] = {0};
    for (int i = 0; i < len; i++) {
        int idx = txt[i] - 'A';
        if (idx >= 0 && idx < 26) counts[idx]++;
    }
    int sum_pairs = 0;
    for (int i = 0; i < 26; i++) sum_pairs += counts[i] * (counts[i] - 1);
    *out_rare = counts['J'-'A'] + counts['Q'-'A'] + counts['X'-'A'] + counts['Z'-'A'];
    return (float)sum_pairs / (float)(len * (len - 1));
}

int main(void) {
    load_quads();

    printf("======================================================================\n");
    printf("EVALUATING PK9-TO-PK10 CROSS-KEY SUBSTITUTION HYPOTHESES\n");
    printf("======================================================================\n");

    // 1. Direct PK9 s28 Keystream on PK10 (Period 28, 18 cycles)
    printf("\n--- Test 1: Direct PK9 s28 Keystream on PK10 (504 = 18 x 28) ---\n");
    for (int mode = 0; mode < 4; mode++) {
        const char *mname = (mode == 0) ? "Vigenere (Kryptos - s28)" :
                            (mode == 1) ? "Beaufort (s28 - Kryptos)" :
                            (mode == 2) ? "Vigenere (Standard - s28)" :
                                          "Beaufort (s28 - Standard)";
        char Z_test[N + 1];
        for (int i = 0; i < N; i++) {
            int shift = s28[i % 28];
            if (mode < 2) {
                int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
                int pt_idx = (mode == 0) ? (ct_idx - shift + 26) % 26 : (shift - ct_idx + 26) % 26;
                Z_test[i] = KRYPTOS[pt_idx];
            } else {
                int ct_idx = PK10_CT[i] - 'A';
                int pt_idx = (mode == 2) ? (ct_idx - shift + 26) % 26 : (shift - ct_idx + 26) % 26;
                Z_test[i] = STANDARD[pt_idx];
            }
        }
        Z_test[N] = '\0';
        int rare; float ioc = get_ioc(Z_test, N, &rare);
        printf("%-30s -> Monogram IoC = %.5f | Rare Letters = %d / 504 (%.1f%%)\n",
               mname, ioc, rare, rare/504.0f*100.0f);
    }

    // 2. PK9 Plaintext Running Key Sweeps
    printf("\n--- Test 2: PK9 135-char Plaintext Running Key across Offsets ---\n");
    int pt_len = strlen(pk9_core_pt);
    float best_rk_ioc = 0.0f;
    int best_rk_offset = 0;
    int best_rk_mode = 0;

    for (int mode = 0; mode < 2; mode++) {
        for (int offset = 0; offset < pt_len; offset++) {
            char Z_rk[N + 1];
            for (int i = 0; i < N; i++) {
                char kchar = pk9_core_pt[(i + offset) % pt_len];
                int shift = strchr(KRYPTOS, kchar) - KRYPTOS;
                int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
                int pt_idx = (mode == 0) ? (ct_idx - shift + 26) % 26 : (shift - ct_idx + 26) % 26;
                Z_rk[i] = KRYPTOS[pt_idx];
            }
            Z_rk[N] = '\0';
            int rare; float ioc = get_ioc(Z_rk, N, &rare);
            if (ioc > best_rk_ioc) {
                best_rk_ioc = ioc;
                best_rk_offset = offset;
                best_rk_mode = mode;
            }
        }
    }
    printf("Best Running Key IoC: %.5f (Mode=%s, Offset=%d)\n",
           best_rk_ioc, best_rk_mode == 0 ? "Vig" : "Beau", best_rk_offset);

    // 3. Keyword Clocks from PK9
    printf("\n--- Test 3: PK9 Lexical Clocks (DEFUNCT [len 7], RELIEF [len 6], SKEWER [len 6], EAST [len 4]) ---\n");
    const char *keywords[] = {"DEFUNCT", "RELIEF", "SKEWER", "EAST", "SESTIA", "DAMES", "MARIN"};
    int n_kw = sizeof(keywords) / sizeof(keywords[0]);

    for (int ik = 0; ik < n_kw; ik++) {
        const char *kw = keywords[ik];
        int kw_len = strlen(kw);
        char Z_kw[N + 1];
        for (int i = 0; i < N; i++) {
            int shift = strchr(KRYPTOS, kw[i % kw_len]) - KRYPTOS;
            int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
            int pt_idx = (ct_idx - shift + 26) % 26;
            Z_kw[i] = KRYPTOS[pt_idx];
        }
        Z_kw[N] = '\0';
        int rare; float ioc = get_ioc(Z_kw, N, &rare);
        printf("Keyword '%-7s' (len %d) -> Monogram IoC = %.5f | Rare Letters = %d\n",
               kw, kw_len, ioc, rare);
    }

    printf("\n======================================================\n");
    printf("BASELINE COMPARISON:\n");
    printf("PK10 Proven 3-Clock State: Monogram IoC = 0.04563 | Rare Letters = 12 (2.38%%)\n");
    printf("Theoretical Maximum IoC on raw PK10: <= 0.04788\n");
    printf("======================================================\n");

    return 0;
}

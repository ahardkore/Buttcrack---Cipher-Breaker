#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
#include <omp.h>

#define N 504
#define CRIB_LEN 22

static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
    char q[16]; float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int c_idx[N];
static int hpos[256];
static int k_to_std[26];

#include "a_inv_22.inc"

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = hpos[(unsigned char)PK10_CT[i]];
    }
}

static inline float score_text(const int *txt, int len) {
    float sc = 0.0f;
    for (int i = 0; i < len - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (len - 3);
}

// Test a 22-character crib at position 0
float test_crib_pos0(const char *crib, char *full_pt_out) {
    int diff[CRIB_LEN];
    for (int i = 0; i < CRIB_LEN; i++) {
        int p_idx = hpos[(unsigned char)crib[i]];
        diff[i] = (c_idx[i] - p_idx + 26) % 26;
    }

    // Multiply by A_inv_22 to recover the 22 variables
    int vars[22];
    for (int r = 0; r < 22; r++) {
        int sum = 0;
        for (int c = 0; c < 22; c++) {
            sum += A_inv_22[r][c] * diff[c];
        }
        vars[r] = (sum % 26 + 26) % 26;
    }

    int q7[7], q8[8], q9[9];
    for (int i = 0; i < 7; i++) q7[i] = vars[i];
    for (int i = 0; i < 7; i++) q8[i] = vars[7 + i];
    q8[7] = 0;
    for (int i = 0; i < 8; i++) q9[i] = vars[14 + i];
    q9[8] = 0;

    // Fast reject: check quadgrams on positions 22..45 (24 letters)
    int test_pt[24];
    for (int i = 0; i < 24; i++) {
        int pos = 22 + i;
        int k = (q7[pos % 7] + q8[pos % 8] + q9[pos % 9]) % 26;
        int p = (c_idx[pos] - k + 26) % 26;
        test_pt[i] = k_to_std[p];
    }
    float sc_early = score_text(test_pt, 24);
    if (sc_early < -6.5f) return sc_early;

    // Full decrypt
    int pt[N];
    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        pt[i] = k_to_std[p];
    }
    float sc_full = score_text(pt, N);
    if (full_pt_out) {
        for (int i = 0; i < N; i++) full_pt_out[i] = 'A' + pt[i];
        full_pt_out[N] = '\0';
    }
    return sc_full;
}

int main() {
    load_quadgrams();
    init_tables();

    // 1. Load Theophilus Book III clean text
    FILE *f = fopen("theophilus_hendrie.txt", "r");
    if (!f) { printf("Cannot open theophilus_hendrie.txt\n"); return 1; }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *raw = malloc(sz + 1);
    fread(raw, 1, sz, f);
    fclose(f);

    char *clean = malloc(sz + 1);
    int clean_len = 0;
    for (long i = 0; i < sz; i++) {
        if (isalpha(raw[i])) clean[clean_len++] = toupper(raw[i]);
    }
    clean[clean_len] = '\0';
    printf("Loaded Theophilus corpus: %d letters.\n", clean_len);

    printf("Testing all %d 22-letter windows at Position 0 on PK10...\n", clean_len - CRIB_LEN);
    float best_sc = -999.0f;
    char best_crib[32] = "";
    char best_pt[N+1] = "";

    #pragma omp parallel for schedule(dynamic, 1000)
    for (int i = 0; i <= clean_len - CRIB_LEN; i++) {
        char crib[CRIB_LEN + 1];
        memcpy(crib, clean + i, CRIB_LEN);
        crib[CRIB_LEN] = '\0';

        char pt[N+1];
        float sc = test_crib_pos0(crib, pt);

        if (sc > -6.0f) {
            #pragma omp critical
            {
                printf("HIT! Score: %.4f | Crib: %s\n", sc, crib);
                printf("PT (first 80): %.80s\n", pt);
            }
        }

        #pragma omp critical
        {
            if (sc > best_sc) {
                best_sc = sc;
                strcpy(best_crib, crib);
                strcpy(best_pt, pt);
            }
        }
    }

    printf("\n=== Theophilus Scan Complete ===\n");
    printf("Best Score: %.4f | Crib: %s\n", best_sc, best_crib);
    printf("PT: %.100s...\n", best_pt);

    free(raw);
    free(clean);
    return 0;
}

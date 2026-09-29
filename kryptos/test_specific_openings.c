#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 504
#define CRIB_LEN 22

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) exit(1);
    char q[16]; float cnt; double total = 0;
    while (fscanf(f, "%s %f", q, &cnt) == 2) if (strlen(q) == 4) total += cnt;
    rewind(f);
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int c_idx[N];
static int hpos[256];
static int k_to_std[26];

#include "a_inv_22.inc"

void init_tables() {
    for (int i=0; i<26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i=0; i<N; i++) {
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

void test_phrase(const char *phrase) {
    char crib[23];
    int len = strlen(phrase);
    if (len < 22) return;
    strncpy(crib, phrase, 22);
    crib[22] = 0;

    int diff[CRIB_LEN];
    for (int i = 0; i < CRIB_LEN; i++) {
        int p_idx = hpos[(unsigned char)crib[i]];
        diff[i] = (c_idx[i] - p_idx + 26) % 26;
    }

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

    int pt[N];
    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        pt[i] = k_to_std[p];
    }
    float sc_full = score_text(pt, N);
    char pt_str[N+1];
    for (int i = 0; i < N; i++) pt_str[i] = pt[i] + 'A';
    pt_str[N] = 0;

    printf("Score: %.4f | Crib: %.22s | Decrypt: %.60s...\n", sc_full, crib, pt_str);
}

int main() {
    load_quads();
    init_tables();

    const char *phrases[] = {
        "INVESTIGATIONLOGITEMTE",
        "INVESTIGATIONLOGITEMZE",
        "INVESTIGATIONLOGRECORD",
        "INVESTIGATIONLOGENTRYT",
        "THEFINALRECORDINOURARC",
        "IHAVEFOUNDTHEFINALRECO",
        "AFTERTENYEARSSTUDYINGU",
        "ATLASTTHENEEDLEWASCOMP",
        "WHENTHENEEDLEWASCOMPLE",
        "WHENTHEWORKWASFINISHED",
        "NOWTHEWORKWASCOMPLETED",
        "WEHAVEPOLISHEDTHENEEDL",
        "IRETURNEDTOTHEWORKSHOP",
        "THEGOLDENNEEDLEWASPLAC",
        "THEPELLEGRINARCHIVEWAS",
        "THEARCHIVEWASFOUNDINTH",
        "THEKNOTWASFINALLYUNRAV",
        "ONCEUNRAVELEDITREVEALS",
        "THEACCESSIONSAYSITREVE",
        "HAVINGCOMPLETEDMYAPPRE",
        "HAVINGSTUDIEDUNDERHIMF",
        "FORALLPRACTICALPURPOSE",
        "SLOWLYDESPERATELYOUTOF",
        "ITWASTHEEARLIESTMORNIN",
        "BERLINCLOCKNORTHEASTNW",
        "THEMASTERLETMEKEEPTHEO",
        "HELETMEKEEPONEOFMYSOWN",
        "HETOLDMETHATIFISTUDYUN"
    };

    for (int i = 0; i < sizeof(phrases)/sizeof(phrases[0]); i++) {
        test_phrase(phrases[i]);
    }

    return 0;
}

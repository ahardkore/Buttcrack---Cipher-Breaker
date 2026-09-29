#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

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

void single_col_decode(const int *in, int len, int width, const int *order, int *out) {
    int h = len / width;
    int grid[600][32];
    int k = 0;
    for (int m = 0; m < width; m++) {
        int col = order[m];
        for (int r = 0; r < h; r++) {
            grid[r][col] = in[k++];
        }
    }
    int idx = 0;
    for (int r = 0; r < h; r++) {
        for (int c = 0; c < width; c++) {
            out[idx++] = grid[r][c];
        }
    }
}

const char CRIBS[15][32] = {
    "THELOSTARCHIVEOFPELLE",
    "THEARCHIVEOFPELLEGRIN",
    "IUNRAVELEDTHEKNOTANDT",
    "WEUNRAVELEDTHEKNOTAND",
    "THEKNOTWASUNRAVELEDAT",
    "ONCEUNRAVELEDITREVEAL",
    "ONCEUNRAVELEDTHEROUTE",
    "THEROUTETOTHELOSTARCH",
    "INVESTIGATIONLOGITEME",
    "ACCESSIONLOGITEMEIGHT",
    "WITHTHENEEDLEINHANDWE",
    "WITHTHESILVERNEEDLEWE",
    "THENEEDLEPIERCEDTHEKN",
    "HAVINGCOMPLETEDMYTENY",
    "AFTERTENYEARSOFSTUDYI"
};
const int NUM_CRIBS = 15;

typedef struct {
    char word[32];
    int order[32];
} WordOrder;

int load_words(const char *filename, int W, WordOrder *words, int max_words) {
    FILE *f = fopen(filename, "r");
    if (!f) return 0;
    char line[64];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < max_words) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == W) {
            strcpy(words[count].word, w);
            typedef struct { char ch; int orig_idx; } Pair;
            Pair p[32];
            for (int i = 0; i < W; i++) { p[i].ch = w[i]; p[i].orig_idx = i; }
            for (int i = 0; i < W - 1; i++) {
                for (int j = i + 1; j < W; j++) {
                    if (p[j].ch < p[i].ch || (p[j].ch == p[i].ch && p[j].orig_idx < p[i].orig_idx)) {
                        Pair tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                    }
                }
            }
            for (int i = 0; i < W; i++) words[count].order[i] = p[i].orig_idx;
            count++;
        }
    }
    fclose(f);
    return count;
}

void test_double_columnar_pair(int w1, WordOrder *words1, int n1,
                               int w2, WordOrder *words2, int n2) {
    long total_pairs = (long)n1 * n2;
    printf("\n=== Double Columnar (%d, %d): %d x %d = %ld pairs ===\n",
           w1, w2, n1, n2, total_pairs);

    double t0 = omp_get_wtime();

    #pragma omp parallel for schedule(dynamic, 10)
    for (long idx = 0; idx < total_pairs; idx++) {
        int i1 = idx / n2;
        int i2 = idx % n2;

        // In decrypt: undo W2 (order2), then undo W1 (order1)
        int x_indices[N], inter[N], z_indices[N];
        for (int i = 0; i < N; i++) x_indices[i] = i;
        single_col_decode(x_indices, N, w2, words2[i2].order, inter);
        single_col_decode(inter, N, w1, words1[i1].order, z_indices);

        // z_indices[p] is the index in ciphertext that lands at position p of Z
        int z_prefix[CRIB_LEN];
        for (int i = 0; i < CRIB_LEN; i++) {
            z_prefix[i] = c_idx[z_indices[i]];
        }

        for (int crib_idx = 0; crib_idx < NUM_CRIBS; crib_idx++) {
            const char *crib = CRIBS[crib_idx];
            int diff[CRIB_LEN];
            for (int i = 0; i < CRIB_LEN; i++) {
                int p_idx = hpos[(unsigned char)crib[i]];
                diff[i] = (z_prefix[i] - p_idx + 26) % 26;
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

            int test_pt[24];
            for (int i = 0; i < 24; i++) {
                int pos = 22 + i;
                int z_char = c_idx[z_indices[pos]];
                int k = (q7[pos % 7] + q8[pos % 8] + q9[pos % 9]) % 26;
                int p = (z_char - k + 26) % 26;
                test_pt[i] = k_to_std[p];
            }
            float sc_early = score_text(test_pt, 24);
            if (sc_early > -5.7f) {
                int pt[N];
                for (int pos = 0; pos < N; pos++) {
                    int z_char = c_idx[z_indices[pos]];
                    int k = (q7[pos % 7] + q8[pos % 8] + q9[pos % 9]) % 26;
                    int p = (z_char - k + 26) % 26;
                    pt[pos] = k_to_std[p];
                }
                float sc_full = score_text(pt, N);
                if (sc_full > -6.0f) {
                    #pragma omp critical
                    {
                        printf("HIT! Pair: (%s, %s) | Crib: %s | Score: %.4f\n",
                               words1[i1].word, words2[i2].word, crib, sc_full);
                        printf("PT (first 100): ");
                        for (int k = 0; k < 100; k++) printf("%c", 'A' + pt[k]);
                        printf("\n");
                        fflush(stdout);
                    }
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed in %.2f s (%.1f checks/sec)\n",
           elapsed, (double)total_pairs * NUM_CRIBS / elapsed);
}

static WordOrder words7[1000], words8[1000], words9[1000];

int main() {
    load_quadgrams();
    init_tables();

    int n7 = load_words("curated_w7.txt", 7, words7, 1000);
    int n8 = load_words("theophilus_w8.txt", 8, words8, 1000);
    int n9 = load_words("theophilus_w9.txt", 9, words9, 1000);

    printf("Loaded: %d w7, %d w8, %d w9\n", n7, n8, n9);

    // 1. (8, 9)
    test_double_columnar_pair(8, words8, n8, 9, words9, n9);

    // 2. (9, 8)
    test_double_columnar_pair(9, words9, n9, 8, words8, n8);

    // 3. (7, 8)
    test_double_columnar_pair(7, words7, n7, 8, words8, n8);

    // 4. (8, 7)
    test_double_columnar_pair(8, words8, n8, 7, words7, n7);

    // 5. (7, 9)
    test_double_columnar_pair(7, words7, n7, 9, words9, n9);

    // 6. (9, 7)
    test_double_columnar_pair(9, words9, n9, 7, words7, n7);

    return 0;
}

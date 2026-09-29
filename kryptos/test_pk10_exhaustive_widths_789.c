#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504

static const char *pk10_raw = 
"UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVL"
"YWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXAT"
"JMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIG"
"SPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZF"
"TFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQI"
"VHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWK"
"HGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZ"
"WVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int ct[N];

void init() {
    for (int i = 0; i < N; i++) {
        ct[i] = pk10_raw[i] - 'A';
    }
}

// Compute slice IoC at period P
float compute_period_ioc(const int *txt, int len, int p) {
    if (p >= len) return 0.0f;
    double sum_ioc = 0.0;
    int valid_slices = 0;

    for (int s = 0; s < p; s++) {
        int counts[26] = {0};
        int n = 0;
        for (int i = s; i < len; i += p) {
            counts[txt[i]]++;
            n++;
        }
        if (n > 1) {
            int num = 0;
            for (int c = 0; c < 26; c++) {
                num += counts[c] * (counts[c] - 1);
            }
            sum_ioc += (double)num / (n * (n - 1));
            valid_slices++;
        }
    }
    return (valid_slices > 0) ? (float)(sum_ioc / valid_slices) : 0.0f;
}

// Next permutation
int next_perm(int *p, int n) {
    int i = n - 2;
    while (i >= 0 && p[i] >= p[i+1]) i--;
    if (i < 0) return 0;
    int j = n - 1;
    while (p[j] <= p[i]) j--;
    int t = p[i]; p[i] = p[j]; p[j] = t;
    int l = i + 1, r = n - 1;
    while (l < r) {
        t = p[l]; p[l] = p[r]; p[r] = t;
        l++; r--;
    }
    return 1;
}

void test_width(int W) {
    int H = N / W;
    printf("\n=== Testing Width %d (H=%d) ===\n", W, H);

    // Count permutations
    long total_perms = 1;
    for (int i = 2; i <= W; i++) total_perms *= i;
    printf("Total permutations to test: %ld\n", total_perms);

    float best_ioc_72 = 0.0f;
    int best_p_72[16];

    float best_ioc_56 = 0.0f;
    int best_p_56[16];

    float best_ioc_63 = 0.0f;
    int best_p_63[16];

    int p[16];
    for (int i = 0; i < W; i++) p[i] = i;

    int tested = 0;
    do {
        // Model A: CT was written col-by-col with perm p, read row-by-row
        // So in original text Z: Z[r*W + c] = CT[p[c]*H + r]
        int Z_A[N];
        for (int r = 0; r < H; r++) {
            for (int c = 0; c < W; c++) {
                Z_A[r * W + c] = ct[p[c] * H + r];
            }
        }

        float ioc72 = compute_period_ioc(Z_A, N, 72);
        if (ioc72 > best_ioc_72) {
            best_ioc_72 = ioc72;
            memcpy(best_p_72, p, W * sizeof(int));
        }

        float ioc56 = compute_period_ioc(Z_A, N, 56);
        if (ioc56 > best_ioc_56) {
            best_ioc_56 = ioc56;
            memcpy(best_p_56, p, W * sizeof(int));
        }

        float ioc63 = compute_period_ioc(Z_A, N, 63);
        if (ioc63 > best_ioc_63) {
            best_ioc_63 = ioc63;
            memcpy(best_p_63, p, W * sizeof(int));
        }

        tested++;
    } while (next_perm(p, W));

    printf("Width %d Results:\n", W);
    printf("  Best Period 72 IoC: %.4f | Perm: ", best_ioc_72);
    for (int i = 0; i < W; i++) printf("%d ", best_p_72[i]); printf("\n");

    printf("  Best Period 56 IoC: %.4f | Perm: ", best_ioc_56);
    for (int i = 0; i < W; i++) printf("%d ", best_p_56[i]); printf("\n");

    printf("  Best Period 63 IoC: %.4f | Perm: ", best_ioc_63);
    for (int i = 0; i < W; i++) printf("%d ", best_p_63[i]); printf("\n");
}

int main() {
    init();
    test_width(7);
    test_width(8);
    test_width(9);
    return 0;
}

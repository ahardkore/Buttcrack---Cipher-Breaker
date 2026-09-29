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

int next_perm(int *arr, int n) {
    int i = n - 2;
    while (i >= 0 && arr[i] >= arr[i+1]) i--;
    if (i < 0) return 0;
    int j = n - 1;
    while (arr[j] <= arr[i]) j--;
    int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    int l = i + 1, r = n - 1;
    while (l < r) {
        tmp = arr[l]; arr[l] = arr[r]; arr[r] = tmp;
        l++; r--;
    }
    return 1;
}

void test_all_cribs_width(int W, const char cribs[][32], int num_cribs) {
    int H = N / W;
    int total_perms = 1;
    for (int i = 1; i <= W; i++) total_perms *= i;

    printf("\n=== Testing Width=%d on %d cribs (Total checks: %ld) ===\n",
           W, num_cribs, (long)total_perms * num_cribs);

    int (*all_orders)[W] = malloc(total_perms * sizeof(*all_orders));
    int cur_order[W];
    for (int i = 0; i < W; i++) cur_order[i] = i;
    int idx = 0;
    do {
        for (int i = 0; i < W; i++) all_orders[idx][i] = cur_order[i];
        idx++;
    } while (next_perm(cur_order, W));

    // Precompute Z_prefix for all permutations
    int (*all_Z_prefix)[CRIB_LEN] = malloc(total_perms * sizeof(*all_Z_prefix));
    for (int p_idx = 0; p_idx < total_perms; p_idx++) {
        const int *order = all_orders[p_idx];
        for (int i = 0; i < CRIB_LEN; i++) {
            int col = i % W;
            int row = i / W;
            int col_pos = 0;
            while (col_pos < W && order[col_pos] != col) col_pos++;
            all_Z_prefix[p_idx][i] = c_idx[col_pos * H + row];
        }
    }

    double t0 = omp_get_wtime();

    #pragma omp parallel for schedule(dynamic, 10)
    for (int crib_idx = 0; crib_idx < num_cribs; crib_idx++) {
        const char *crib = cribs[crib_idx];
        int crib_p[CRIB_LEN];
        for (int i = 0; i < CRIB_LEN; i++) crib_p[i] = hpos[(unsigned char)crib[i]];

        for (int p_idx = 0; p_idx < total_perms; p_idx++) {
            const int *z_pre = all_Z_prefix[p_idx];
            int diff[CRIB_LEN];
            for (int i = 0; i < CRIB_LEN; i++) {
                diff[i] = (z_pre[i] - crib_p[i] + 26) % 26;
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

            // Early check: positions 22..45 (24 letters)
            const int *order = all_orders[p_idx];
            int test_pt[24];
            for (int i = 0; i < 24; i++) {
                int pos = 22 + i;
                int col = pos % W;
                int row = pos / W;
                int col_pos = 0;
                while (col_pos < W && order[col_pos] != col) col_pos++;
                int z_char = c_idx[col_pos * H + row];
                int k = (q7[pos % 7] + q8[pos % 8] + q9[pos % 9]) % 26;
                int p = (z_char - k + 26) % 26;
                test_pt[i] = k_to_std[p];
            }
            float sc_early = score_text(test_pt, 24);
            if (sc_early > -5.7f) {
                // Full decrypt!
                int pt[N];
                for (int pos = 0; pos < N; pos++) {
                    int col = pos % W;
                    int row = pos / W;
                    int col_pos = 0;
                    while (col_pos < W && order[col_pos] != col) col_pos++;
                    int z_char = c_idx[col_pos * H + row];
                    int k = (q7[pos % 7] + q8[pos % 8] + q9[pos % 9]) % 26;
                    int p = (z_char - k + 26) % 26;
                    pt[pos] = k_to_std[p];
                }
                float sc_full = score_text(pt, N);
                if (sc_full > -6.0f) {
                    #pragma omp critical
                    {
                        printf("HIT! W=%d Score=%.4f Crib=%s Order=", W, sc_full, crib);
                        for (int k = 0; k < W; k++) printf("%d ", order[k]);
                        printf("\nPT (first 100): ");
                        for (int k = 0; k < 100; k++) printf("%c", 'A' + pt[k]);
                        printf("\n");
                        fflush(stdout);
                    }
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("W=%d completed in %.2f s (%.1f checks/sec)\n",
           W, elapsed, (double)total_perms * num_cribs / elapsed);

    free(all_orders);
    free(all_Z_prefix);
}

int main() {
    load_quadgrams();
    init_tables();

    FILE *f = fopen("pk10_narrative_cribs.txt", "r");
    if (!f) { printf("Cannot open pk10_narrative_cribs.txt\n"); return 1; }
    static char cribs[5000][32];
    int num_cribs = 0;
    char line[64];
    while (fgets(line, sizeof(line), f) && num_cribs < 5000) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == 22) {
            strcpy(cribs[num_cribs++], w);
        }
    }
    fclose(f);
    printf("Loaded %d narrative cribs.\n", num_cribs);

    test_all_cribs_width(7, cribs, num_cribs);
    test_all_cribs_width(8, cribs, num_cribs);

    return 0;
}

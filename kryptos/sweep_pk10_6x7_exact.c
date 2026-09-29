#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define W 42
#define H 12
#define W_A 6
#define H_A 7
#define W_B 7
#define H_B 6

static float quad[26][26][26][26];

void load_quads() {
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
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int c_idx[N];
static int alpha_to_std[26];
static int Z[N];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
    }

    const int Q7_PK[7] = {0, 22, 3, 3, 15, 0, 1};
    const int q8[8] = {22, 15, 5, 9, 20, 6, 4, 6};
    const int q9[9] = {23, 2, 25, 22, 18, 9, 13, 13, 24};

    for (int i = 0; i < N; i++) {
        int k = (Q7_PK[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        Z[i] = alpha_to_std[p];
    }
}

// Pre-generate all 720 permutations of 6 elements
static int perms6[720][6];
static int n_perms6 = 0;

void gen6(int *arr, int l, int r) {
    if (l == r) {
        memcpy(perms6[n_perms6++], arr, 6 * sizeof(int));
        return;
    }
    for (int i = l; i <= r; i++) {
        int t = arr[l]; arr[l] = arr[i]; arr[i] = t;
        gen6(arr, l + 1, r);
        t = arr[l]; arr[l] = arr[i]; arr[i] = t;
    }
}

// Pre-generate all 5040 permutations of 7 elements
static int perms7[5040][7];
static int n_perms7 = 0;

void gen7(int *arr, int l, int r) {
    if (l == r) {
        memcpy(perms7[n_perms7++], arr, 7 * sizeof(int));
        return;
    }
    for (int i = l; i <= r; i++) {
        int t = arr[l]; arr[l] = arr[i]; arr[i] = t;
        gen7(arr, l + 1, r);
        t = arr[l]; arr[l] = arr[i]; arr[i] = t;
    }
}

// Compose a 42-element permutation from a 6-element and 7-element permutation:
// Layout 42 as 7 rows of 6 cols (or 6 rows of 7 cols):
// Option 1: grid (7x6) -> col perm p6 -> row perm p7 -> read by rows
static inline void make_perm_7x6(const int *p6, const int *p7, int *out_perm) {
    int idx = 0;
    for (int r = 0; r < 7; r++) {
        int orig_r = p7[r];
        for (int c = 0; c < 6; c++) {
            int orig_c = p6[c];
            out_perm[idx++] = orig_r * 6 + orig_c;
        }
    }
}

// Option 2: grid (6x7) -> col perm p7 -> row perm p6 -> read by rows
static inline void make_perm_6x7(const int *p7, const int *p6, int *out_perm) {
    int idx = 0;
    for (int r = 0; r < 6; r++) {
        int orig_r = p6[r];
        for (int c = 0; c < 7; c++) {
            int orig_c = p7[c];
            out_perm[idx++] = orig_r * 7 + orig_c;
        }
    }
}

static inline float eval_perm(const int *perm) {
    int pt[N];
    int idx = 0;
    for (int r = 0; r < H; r++) {
        int base = r * W;
        for (int c = 0; c < W; c++) {
            pt[idx++] = Z[base + perm[c]];
        }
    }
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    load_quads();
    init_tables();

    int b6[6] = {0, 1, 2, 3, 4, 5}; gen6(b6, 0, 5);
    int b7[7] = {0, 1, 2, 3, 4, 5, 6}; gen7(b7, 0, 6);

    printf("======================================================================\n");
    printf("PK10 Exhaustive 6x7 and 7x6 Compound Permutation Sweep\n");
    printf("Permutations to Evaluate: %d x %d = %d pairs\n", n_perms6, n_perms7, n_perms6 * n_perms7);
    printf("======================================================================\n\n");

    float global_best_sc = -999.0f;
    int best_p6[6], best_p7[7], best_type = 0;
    int best_perm[W];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float loc_best_sc = -999.0f;
        int loc_p6[6], loc_p7[7], loc_type = 0, loc_perm[W];

        #pragma omp for schedule(dynamic, 10)
        for (int i = 0; i < n_perms6; i++) {
            int p42[W];
            for (int j = 0; j < n_perms7; j++) {
                // Type 1: 7x6
                make_perm_7x6(perms6[i], perms7[j], p42);
                float sc1 = eval_perm(p42);
                if (sc1 > loc_best_sc) {
                    loc_best_sc = sc1;
                    loc_type = 1;
                    memcpy(loc_p6, perms6[i], 6 * sizeof(int));
                    memcpy(loc_p7, perms7[j], 7 * sizeof(int));
                    memcpy(loc_perm, p42, W * sizeof(int));
                }

                // Type 2: 6x7
                make_perm_6x7(perms7[j], perms6[i], p42);
                float sc2 = eval_perm(p42);
                if (sc2 > loc_best_sc) {
                    loc_best_sc = sc2;
                    loc_type = 2;
                    memcpy(loc_p6, perms6[i], 6 * sizeof(int));
                    memcpy(loc_p7, perms7[j], 7 * sizeof(int));
                    memcpy(loc_perm, p42, W * sizeof(int));
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                best_type = loc_type;
                memcpy(best_p6, loc_p6, 6 * sizeof(int));
                memcpy(best_p7, loc_p7, 7 * sizeof(int));
                memcpy(best_perm, loc_perm, W * sizeof(int));
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("SWEEP COMPLETED (7,257,600 evaluations in %.3f s)\n", elapsed);
    printf("======================================================================\n");
    printf("Best Score: %.4f\n", global_best_sc);
    printf("Best Type: %s\n", best_type == 1 ? "7x6 (rows 7, cols 6)" : "6x7 (rows 6, cols 7)");
    printf("P6: [");
    for (int i = 0; i < 6; i++) printf("%d%s", best_p6[i], i==5?"":", ");
    printf("]\n");
    printf("P7: [");
    for (int i = 0; i < 7; i++) printf("%d%s", best_p7[i], i==6?"":", ");
    printf("]\n");
    printf("Resulting Order (W=42): [");
    for (int i = 0; i < W; i++) printf("%d%s", best_perm[i], i==W-1?"":", ");
    printf("]\n\n");

    char pt[N + 1];
    int idx = 0;
    for (int r = 0; r < H; r++) {
        int base = r * W;
        for (int c = 0; c < W; c++) {
            pt[idx++] = 'A' + Z[base + best_perm[c]];
        }
    }
    pt[N] = '\0';

    printf("Full Plaintext:\n%s\n\n", pt);
    printf("Plaintext layout in 12 rows of 42 chars:\n");
    for (int r = 0; r < H; r++) {
        char buf[W + 1];
        memcpy(buf, pt + r * W, W);
        buf[W] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}

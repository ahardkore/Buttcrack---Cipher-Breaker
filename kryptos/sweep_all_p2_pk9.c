#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W1 18
#define H1 8
#define W2 8
#define H2 18

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
const char *PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int k2std[26];
static int hpos[256];
static int Z[N];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK9_RAW[i]];

    const int s[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};
    for (int t = 0; t < N; t++) {
        int shift = s[t % 28];
        int p_kr = (ct_kr[t] - shift + 26) % 26;
        Z[t] = k2std[p_kr];
    }
}

static const int p1[W1] = {5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6};

static inline void invert_col(const int *src, int w, int h, const int *perm, int *dst) {
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < h; r++) {
            dst[r * w + col] = src[idx++];
        }
    }
}

static inline float eval_p2(const int *p2, int *out_pt) {
    int mid[N], pt[N];
    invert_col(Z, W2, H2, p2, mid);
    invert_col(mid, W1, H1, p1, pt);

    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

// Generate all 40,320 permutations of 8 elements
static int all_perms[40320][8];
static int perm_count = 0;

void generate_perms(int *arr, int l, int r) {
    if (l == r) {
        memcpy(all_perms[perm_count++], arr, 8 * sizeof(int));
        return;
    }
    for (int i = l; i <= r; i++) {
        int t = arr[l]; arr[l] = arr[i]; arr[i] = t;
        generate_perms(arr, l + 1, r);
        t = arr[l]; arr[l] = arr[i]; arr[i] = t;
    }
}

int main() {
    load_quads();
    init_tables();

    int base_arr[8] = {0, 1, 2, 3, 4, 5, 6, 7};
    generate_perms(base_arr, 0, 7);

    printf("======================================================================\n");
    printf("PK9 Exhaustive 8! Permutation Sweep on Stage 2 (P2) with P1 Fixed\n");
    printf("Total Permutations to Evaluate: %d\n", perm_count);
    printf("======================================================================\n\n");

    float global_best_sc = -999.0f;
    int best_p2[8];
    char best_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float loc_best_sc = -999.0f;
        int loc_best_p2[8];
        char loc_pt[N + 1];
        int pt[N];

        #pragma omp for schedule(static)
        for (int i = 0; i < perm_count; i++) {
            float sc = eval_p2(all_perms[i], pt);
            if (sc > loc_best_sc) {
                loc_best_sc = sc;
                memcpy(loc_best_p2, all_perms[i], 8 * sizeof(int));
                for (int k = 0; k < N; k++) loc_pt[k] = 'A' + pt[k];
                loc_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(best_p2, loc_best_p2, 8 * sizeof(int));
                strcpy(best_pt, loc_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("EXHAUSTIVE 8! SWEEP COMPLETED in %.4f s\n", elapsed);
    printf("======================================================================\n");
    printf("Global Best Score: %.4f\n", global_best_sc);
    printf("Proven Optimal P2 (len 8): [");
    for (int i = 0; i < 8; i++) printf("%d%s", best_p2[i], i==7?"":", ");
    printf("]\n\n");

    printf("Full Plaintext:\n%s\n\n", best_pt);
    printf("Plaintext layout in 8 rows of 18 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[W1 + 1];
        memcpy(buf, best_pt + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}

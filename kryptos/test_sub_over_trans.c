#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *CT9 = "HEAQVHGZJGSYHEUBYFHJSQNHSEHAWFLHXAQBLQGZGSMLSEZYSJMQYYLHDUHLCPSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSEUFBVBXJXMMHIRHUKQQLYAGUJYIEJXDMALIFUTAIHZRPFF";
static int C[144];
static int N = 144;

void init() {
    for (int i = 0; i < 26; i++) {
        for (int j = 0; j < 26; j++) {
            for (int k = 0; k < 26; k++) {
                for (int l = 0; l < 26; l++) {
                    quad_table[i][j][k][l] = -9.0f;
                }
            }
        }
    }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { fprintf(stderr, "Cannot open quads\n"); exit(1); }
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
    for (int i = 0; i < N; i++) {
        C[i] = std_to_k[CT9[i] - 'A'];
    }
}

// Permutations generator
static int perms8[40320][8];
static int num_perms8 = 0;

void gen_perms8(int *arr, int l, int r) {
    if (l == r) {
        for (int i = 0; i < 8; i++) perms8[num_perms8][i] = arr[i];
        num_perms8++;
        return;
    }
    for (int i = l; i <= r; i++) {
        int t = arr[l]; arr[l] = arr[i]; arr[i] = t;
        gen_perms8(arr, l + 1, r);
        t = arr[l]; arr[l] = arr[i]; arr[i] = t;
    }
}

static int perms6[720][6];
static int num_perms6 = 0;

void gen_perms6(int *arr, int l, int r) {
    if (l == r) {
        for (int i = 0; i < 6; i++) perms6[num_perms6][i] = arr[i];
        num_perms6++;
        return;
    }
    for (int i = l; i <= r; i++) {
        int t = arr[l]; arr[l] = arr[i]; arr[i] = t;
        gen_perms6(arr, l + 1, r);
        t = arr[l]; arr[l] = arr[i]; arr[i] = t;
    }
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    init();

    int a8[8] = {0, 1, 2, 3, 4, 5, 6, 7};
    gen_perms8(a8, 0, 7);
    int a6[6] = {0, 1, 2, 3, 4, 5};
    gen_perms6(a6, 0, 5);

    printf("Precomputed %d perms for width 8, %d perms for width 6.\n", num_perms8, num_perms6);

    const char *thematic_keys[] = {
        "KRYPTOS", "WEBSTER", "WOMACKA", "WILLIAM", "SANBORN", "SCHEIDT", "LANGLEY",
        "BERLINS", "GERMANY", "AMERICA", "HEARTHS", "NEEDLES", "WHITESM", "WORKSHO",
        "ANVILSS", "BELLOWS", "HAMMERS", "METALLS", "IRONBAR", "COPPERT", "DRAWPLT",
        "PELLEGR", "VIENNAS", "AUSTRIA", "LEIPZIG", "EASTNNE", "PALIMPS", "ABSCISS",
        "PORTALS", "SEVENTH", "FIFTEEN", "FOURTEE", "SIXTEEN", "TWENTYF", "NIMBLES",
        "WIMBLES", "WINDLES", "TROWELS", "TONGSSS", "CHISELS", "PLIERSN", "SPINDLE",
        "THIMBLE", "SHUTTLE", "BOBBINS", "LOOMSSS", "WEAVERS", "SPINNER", "TAILORS",
        "QUENCHS", "TEMPERS", "ANNEALS", "FORGING", "CRUCIBL", "FURNACE", "CASTING"
    };
    int num_keys = sizeof(thematic_keys) / sizeof(thematic_keys[0]);

    float global_best = -999.0f;
    char best_key[16] = "";
    int best_w = 0;
    int best_p[16]; (void)best_p;
    char best_pt[160] = "";

    for (int k = 0; k < num_keys; k++) {
        const char *kw = thematic_keys[k];
        int shifts[7];
        for (int i = 0; i < 7; i++) shifts[i] = std_to_k[kw[i] - 'A'];

        // Mode 1: Quagmire III (P' = (C - shift) mod 26)
        int P_prime[144];
        for (int i = 0; i < N; i++) {
            P_prime[i] = (C[i] - shifts[i % 7] + 26) % 26;
        }

        // Test width 6: 144 / 6 = 24 rows
        // Write P_prime into grid:
        // Transposition convention 1: P_prime was read column by column from P (written row by row)
        // P[r][c] = P_prime[perm[c] * 24 + r]
        // Let's test both reading and writing conventions:
        // Conv A: P_prime is columnar output. Grid has W columns, H = 144/W rows.
        // The c-th column in P_prime corresponds to perm[c]-th column of grid.
        for (int pi = 0; pi < num_perms6; pi++) {
            int *perm = perms6[pi];
            int P_dec[144];
            int idx = 0;
            for (int r = 0; r < 24; r++) {
                for (int c = 0; c < 6; c++) {
                    P_dec[idx++] = k_to_std[P_prime[perm[c] * 24 + r]];
                }
            }
            float sc = 0.0f;
            for (int i = 0; i < N - 3; i++) {
                sc += quad_table[P_dec[i]][P_dec[i+1]][P_dec[i+2]][P_dec[i+3]];
            }
            sc /= (N - 3);
            if (sc > global_best) {
                global_best = sc;
                strcpy(best_key, kw);
                best_w = 6;
                for (int i = 0; i < 6; i++) best_p[i] = perm[i];
                for (int i = 0; i < N; i++) best_pt[i] = P_dec[i] + 'A';
                best_pt[N] = '\0';
                printf("New best! sc=%.3f | kw=%s, w=6 | PT: %.50s...\n", sc, kw, best_pt);
            }
        }

        // Test width 8: 144 / 8 = 18 rows
        for (int pi = 0; pi < num_perms8; pi++) {
            int *perm = perms8[pi];
            int P_dec[144];
            int idx = 0;
            for (int r = 0; r < 18; r++) {
                for (int c = 0; c < 8; c++) {
                    P_dec[idx++] = k_to_std[P_prime[perm[c] * 18 + r]];
                }
            }
            float sc = 0.0f;
            for (int i = 0; i < N - 3; i++) {
                sc += quad_table[P_dec[i]][P_dec[i+1]][P_dec[i+2]][P_dec[i+3]];
            }
            sc /= (N - 3);
            if (sc > global_best) {
                global_best = sc;
                strcpy(best_key, kw);
                best_w = 8;
                for (int i = 0; i < 8; i++) best_p[i] = perm[i];
                for (int i = 0; i < N; i++) best_pt[i] = P_dec[i] + 'A';
                best_pt[N] = '\0';
                printf("New best! sc=%.3f | kw=%s, w=8 | PT: %.50s...\n", sc, kw, best_pt);
            }
        }
    }

    printf("\nFinished sweep of %d thematic keys.\n", num_keys);
    printf("Global best: %.3f with key %s (width %d)\n", global_best, best_key, best_w);
    printf("PT: %s\n", best_pt);
    return 0;
}

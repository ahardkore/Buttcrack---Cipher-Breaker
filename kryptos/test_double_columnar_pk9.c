#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *CT9 = "HEAQVHGZJGSYHEUBYFHJSQNHSEHAWFLHXAQBLQGZGSMLSEZYSJMQYYLHDUHLCPSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSEUFBVBXJXMMHIRHUKQQLYAGUJYIEJXDMALIFUTAIHZRPFF";
static int C[144];
static const int N = 144;

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

static int perms6[720][6];
static int n_perms6 = 0;
void gen6(int *arr, int l, int r) {
    if (l == r) {
        for (int i = 0; i < 6; i++) perms6[n_perms6][i] = arr[i];
        n_perms6++;
        return;
    }
    for (int i = l; i <= r; i++) {
        int t = arr[l]; arr[l] = arr[i]; arr[i] = t;
        gen6(arr, l+1, r);
        t = arr[l]; arr[l] = arr[i]; arr[i] = t;
    }
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    init();

    int a6[6] = {0, 1, 2, 3, 4, 5};
    gen6(a6, 0, 5);

    const char *thematic_keys[] = {
        "KRYPTOS", "WEBSTER", "WOMACKA", "WILLIAM", "SANBORN", "SCHEIDT", "LANGLEY",
        "BERLINS", "GERMANY", "AMERICA", "HEARTHS", "NEEDLES", "WHITESM", "WORKSHO",
        "PORTALS", "SEVENTH", "FIFTEEN"
    };
    int n_keys = sizeof(thematic_keys)/sizeof(thematic_keys[0]);

    printf("Testing Double Columnar (6x24, 6x24) across %d keys (518,400 per key)...\n", n_keys);

    float global_best = -999.0f;
    char best_kw[16] = "";
    int best_o1[6] = {0}, best_o2[6] = {0};
    char best_pt[150] = "";

    // Width 6: H = 144 / 6 = 24
    int H = 24;

    for (int ki = 0; ki < n_keys; ki++) {
        const char *kw = thematic_keys[ki];
        int shifts[7];
        for (int i = 0; i < 7; i++) shifts[i] = std_to_k[kw[i] - 'A'];

        int P_prime[144];
        for (int i = 0; i < N; i++) {
            P_prime[i] = (C[i] - shifts[i % 7] + 26) % 26;
        }

        // Test all pairs (o1, o2)
        // Step 1: Undo columnar 2 (o2):
        // P_prime has 6 columns of length 24. Column c is placed at order o2[c].
        // Row r, col c: T1[r * 6 + c] = P_prime[col_idx * 24 + r] where order[col_idx] = c.
        // Precompute inverted orders:
        for (int p2 = 0; p2 < n_perms6; p2++) {
            int *o2 = perms6[p2];
            int inv_o2[6];
            for (int i = 0; i < 6; i++) inv_o2[o2[i]] = i;

            int T1[144];
            int idx = 0;
            for (int r = 0; r < H; r++) {
                for (int c = 0; c < 6; c++) {
                    T1[idx++] = P_prime[inv_o2[c] * H + r];
                }
            }

            // Step 2: Undo columnar 1 (o1) on T1:
            for (int p1 = 0; p1 < n_perms6; p1++) {
                int *o1 = perms6[p1];
                int inv_o1[6];
                for (int i = 0; i < 6; i++) inv_o1[o1[i]] = i;

                int P_dec[144];
                int pidx = 0;
                for (int r = 0; r < H; r++) {
                    for (int c = 0; c < 6; c++) {
                        P_dec[pidx++] = k_to_std[T1[inv_o1[c] * H + r]];
                    }
                }

                float sc = 0.0f;
                for (int i = 0; i < N - 3; i++) {
                    sc += quad_table[P_dec[i]][P_dec[i+1]][P_dec[i+2]][P_dec[i+3]];
                }
                sc /= (N - 3);

                if (sc > global_best) {
                    global_best = sc;
                    strcpy(best_kw, kw);
                    for (int i = 0; i < 6; i++) { best_o1[i] = o1[i]; best_o2[i] = o2[i]; }
                    for (int i = 0; i < N; i++) best_pt[i] = P_dec[i] + 'A';
                    best_pt[N] = '\0';
                    printf("New best: sc=%.3f | kw=%s | o1=[%d,%d,%d,%d,%d,%d], o2=[%d,%d,%d,%d,%d,%d]\n",
                           sc, kw, o1[0], o1[1], o1[2], o1[3], o1[4], o1[5],
                           o2[0], o2[1], o2[2], o2[3], o2[4], o2[5]);
                    printf("PT: %.60s...\n", best_pt);
                    fflush(stdout);
                }
            }
        }
    }

    printf("\nFinished. Global best: %.3f with key %s\n", global_best, best_kw);
    printf("PT: %s\n", best_pt);
    return 0;
}

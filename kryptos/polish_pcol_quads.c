#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define W 12
#define H 12

static const char *G_rows[12] = {
    "UIRERTAHIHIO",
    "TSMRLOCNSDHH",
    "NWOWEMOSALSO",
    "MDTUNRNAUENO",
    "SOIHFSNLIRSN",
    "ASSETIRNFNSW",
    "OCEHMAHADCAE",
    "FTGTDNIONOCE",
    "WFETREEEEPSD",
    "SALRNEEIFDIH",
    "UITAONLOFSSI",
    "EHAHSSDSOOFU"
};

static int G[12][12];
static float quadgrams[26][26][26][26];

void load_quads() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    quadgrams[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    char line[64];
    double total = 5348433.0;
    while (fgets(line, sizeof(line), f)) {
        char g[5]; double cnt;
        if (sscanf(line, "%4s %lf", g, &cnt) == 2) {
            int a = g[0]-'A', b = g[1]-'A', c = g[2]-'A', d = g[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quadgrams[a][b][c][d] = (float)log10(cnt / total);
            }
        }
    }
    fclose(f);
}

static inline float eval_pcol(const int *p_col) {
    float sc = 0;
    for (int r = 0; r < 12; r++) {
        int l0 = G[r][p_col[0]];
        int l1 = G[r][p_col[1]];
        int l2 = G[r][p_col[2]];
        int l3;
        for (int c = 3; c < 12; c++) {
            l3 = G[r][p_col[c]];
            sc += quadgrams[l0][l1][l2][l3];
            l0 = l1; l1 = l2; l2 = l3;
        }
    }
    return sc / (12 * 9);
}

static inline unsigned int xorshift32(unsigned int *state) {
    unsigned int x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

int main(int argc, char **argv) {
    load_quads();

    for (int r=0; r<12; r++) {
        for (int c=0; c<12; c++) {
            G[r][c] = G_rows[r][c] - 'A';
        }
    }

    int base_perm[12] = {9, 10, 3, 2, 7, 8, 11, 5, 4, 0, 6, 1};
    printf("Initial Held-Karp permutation quadgram score: %.4f\n", eval_pcol(base_perm));

    // Exhaustive 2-opt and 3-opt polish
    int best_perm[12];
    memcpy(best_perm, base_perm, sizeof(base_perm));
    float best_sc = eval_pcol(best_perm);

    int improved = 1;
    while (improved) {
        improved = 0;
        // 2-opt swaps
        for (int i=0; i<11; i++) {
            for (int j=i+1; j<12; j++) {
                int p[12];
                memcpy(p, best_perm, sizeof(p));
                int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                float sc = eval_pcol(p);
                if (sc > best_sc + 1e-5) {
                    best_sc = sc;
                    memcpy(best_perm, p, sizeof(p));
                    improved = 1;
                    printf("2-opt improved to %.4f\n", best_sc);
                }
            }
        }
        // 2-opt reverse segments
        for (int i=0; i<11; i++) {
            for (int j=i+1; j<12; j++) {
                int p[12];
                memcpy(p, best_perm, sizeof(p));
                for (int k=0; k<=(j-i)/2; k++) {
                    int tmp = p[i+k]; p[i+k] = p[j-k]; p[j-k] = tmp;
                }
                float sc = eval_pcol(p);
                if (sc > best_sc + 1e-5) {
                    best_sc = sc;
                    memcpy(best_perm, p, sizeof(p));
                    improved = 1;
                    printf("Segment reverse improved to %.4f\n", best_sc);
                }
            }
        }
        // Insertions
        for (int i=0; i<12; i++) {
            for (int j=0; j<12; j++) {
                if (i == j) continue;
                int p[12];
                int val = best_perm[i];
                int idx = 0;
                for (int k=0; k<12; k++) {
                    if (k == i) continue;
                    if (idx == j) p[idx++] = val;
                    p[idx++] = best_perm[k];
                }
                if (idx == j) p[idx++] = val;
                float sc = eval_pcol(p);
                if (sc > best_sc + 1e-5) {
                    best_sc = sc;
                    memcpy(best_perm, p, sizeof(p));
                    improved = 1;
                    printf("Insertion improved to %.4f\n", best_sc);
                }
            }
        }
    }

    printf("\nPolished Best Score: %.4f\n", best_sc);
    printf("Optimal p_col: [");
    for (int k=0; k<12; k++) printf("%d%s", best_perm[k], k<11?", ":"]\n");

    printf("\nDecrypted Rows with polished p_col:\n");
    for (int r = 0; r < 12; r++) {
        char line[13];
        for (int c = 0; c < 12; c++) {
            line[c] = G[r][best_perm[c]] + 'A';
        }
        line[12] = 0;
        printf("Row %2d: %s\n", r, line);
    }

    return 0;
}

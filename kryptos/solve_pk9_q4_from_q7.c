#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

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
const char *UNDONE = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

static int ct_kr[N];
static int k2std[26];
static int hpos[256];

static inline float score_pt(const int *pt_std) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return s / (N - 3);
}

int main() {
    load_quads();
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)UNDONE[i]];
    }

    int top_q7[5][7] = {
        {0, 1, 22, 18, 4, 23, 12},
        {0, 5, 0, 22, 8, 1, 16},
        {0, 5, 4, 0, 12, 1, 16},
        {0, 1, 0, 22, 8, 23, 12},
        {0, 1, 20, 18, 2, 23, 12}
    };

    for (int cand = 0; cand < 5; cand++) {
        int *q7 = top_q7[cand];
        printf("--- Testing q7 candidate %d: [%d, %d, %d, %d, %d, %d, %d] ---\n",
               cand + 1, q7[0], q7[1], q7[2], q7[3], q7[4], q7[5], q7[6]);

        float best_sc = -999.0f;
        int best_q4[4];
        char best_pt[N + 1];

        #pragma omp parallel
        {
            float loc_best = -999.0f;
            int loc_q4[4];
            char loc_pt[N + 1];

            #pragma omp for schedule(dynamic, 1)
            for (int k0 = 0; k0 < 26; k0++) {
                int q4[4];
                q4[0] = k0;
                for (int k1 = 0; k1 < 26; k1++) {
                    q4[1] = k1;
                    for (int k2 = 0; k2 < 26; k2++) {
                        q4[2] = k2;
                        for (int k3 = 0; k3 < 26; k3++) {
                            q4[3] = k3;

                            int pt[N];
                            for (int t = 0; t < N; t++) {
                                int k_sum = (q4[t % 4] + q7[t % 7]) % 26;
                                int p_kr = (ct_kr[t] - k_sum + 26) % 26;
                                pt[t] = k2std[p_kr];
                            }

                            float sc = score_pt(pt);
                            if (sc > loc_best) {
                                loc_best = sc;
                                memcpy(loc_q4, q4, 4 * sizeof(int));
                                for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                                loc_pt[N] = '\0';
                            }
                        }
                    }
                }
            }

            #pragma omp critical
            {
                if (loc_best > best_sc) {
                    best_sc = loc_best;
                    memcpy(best_q4, loc_q4, 4 * sizeof(int));
                    strcpy(best_pt, loc_pt);
                }
            }
        }

        printf("Best Score: %.4f | q4: [%d, %d, %d, %d] (KR: %c%c%c%c)\n",
               best_sc, best_q4[0], best_q4[1], best_q4[2], best_q4[3],
               KRYPTOS[best_q4[0]], KRYPTOS[best_q4[1]], KRYPTOS[best_q4[2]], KRYPTOS[best_q4[3]]);
        printf("PT: %s\n\n", best_pt);
    }

    return 0;
}

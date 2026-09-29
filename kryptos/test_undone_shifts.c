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
static int ct_std[N];
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
        ct_std[i] = UNDONE[i] - 'A';
    }

    int c1[5] = {10, 2, 6, 14, 17};
    int c2[5] = {9, 13, 11, 7, 25};
    int c3[5] = {7, 1, 5, 23, 2};
    int c4[5] = {21, 17, 9, 13, 3};
    int c5[5] = {10, 3, 2, 6, 9};
    int c6[5] = {21, 18, 0, 22, 1};

    float global_best = -999.0f;
    int best_k[7];
    char best_pt[N+1];

    #pragma omp parallel
    {
        float loc_best = -999.0f;
        int loc_k[7];
        char loc_pt[N+1];

        #pragma omp for schedule(dynamic, 1)
        for (int k0 = 0; k0 < 26; k0++) {
            for (int i1 = 0; i1 < 5; i1++) {
                int k1 = c1[i1];
                for (int i2 = 0; i2 < 5; i2++) {
                    int k2 = c2[i2];
                    for (int i3 = 0; i3 < 5; i3++) {
                        int k3 = c3[i3];
                        for (int i4 = 0; i4 < 5; i4++) {
                            int k4 = c4[i4];
                            for (int i5 = 0; i5 < 5; i5++) {
                                int k5 = c5[i5];
                                for (int i6 = 0; i6 < 5; i6++) {
                                    int k6 = c6[i6];
                                    int key[7] = {k0, k1, k2, k3, k4, k5, k6};

                                    int pt[N];
                                    for (int t = 0; t < N; t++) {
                                        int p_kr = (ct_kr[t] - key[t % 7] + 26) % 26;
                                        pt[t] = k2std[p_kr];
                                    }

                                    float sc = score_pt(pt);
                                    if (sc > loc_best) {
                                        loc_best = sc;
                                        memcpy(loc_k, key, 7 * sizeof(int));
                                        for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                                        loc_pt[N] = '\0';
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best > global_best) {
                global_best = loc_best;
                memcpy(best_k, loc_k, 7 * sizeof(int));
                strcpy(best_pt, loc_pt);
            }
        }
    }

    printf("Best Q3 Key: ");
    for (int i = 0; i < 7; i++) printf("%c", KRYPTOS[best_k[i]]);
    printf(" | Score: %.4f\n", global_best);
    printf("PT: %s\n", best_pt);

    return 0;
}

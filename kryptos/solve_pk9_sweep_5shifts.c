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

static inline float eval_shifts(const int *shifts, int *out_pt) {
    int pt[N];
    for (int t = 0; t < N; t++) {
        int s = shifts[t % 14];
        int p_kr = (ct_kr[t] - s + 26) % 26;
        pt[t] = k2std[p_kr];
    }
    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
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

    printf("======================================================================\n");
    printf("Sweeping all 11.88M configurations with prefix BYAACY and core OHG\n");
    printf("======================================================================\n");

    int base_shifts[14] = {
        8,  // B
        2,  // Y
        7,  // A
        7,  // A
        9,  // C
        2,  // Y
        0,  // s6 free
        5,  // O
        14, // H
        13, // G
        0,  // s10 free
        0,  // s11 free
        0,  // s12 free
        0   // s13 free
    };

    float global_best_sc = -999.0f;
    int g_s6, g_s10, g_s11, g_s12, g_s13;
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float loc_best_sc = -999.0f;
        int l_s6 = 0, l_s10 = 0, l_s11 = 0, l_s12 = 0, l_s13 = 0;
        char l_pt[N + 1];

        #pragma omp for collapse(2) schedule(dynamic, 1)
        for (int s6 = 0; s6 < 26; s6++) {
            for (int s10 = 0; s10 < 26; s10++) {
                int shifts[14];
                memcpy(shifts, base_shifts, 14 * sizeof(int));
                shifts[6] = s6;
                shifts[10] = s10;

                for (int s11 = 0; s11 < 26; s11++) {
                    shifts[11] = s11;
                    for (int s12 = 0; s12 < 26; s12++) {
                        shifts[12] = s12;
                        for (int s13 = 0; s13 < 26; s13++) {
                            shifts[13] = s13;

                            float sc = eval_shifts(shifts, NULL);
                            if (sc > loc_best_sc) {
                                loc_best_sc = sc;
                                l_s6 = s6;
                                l_s10 = s10;
                                l_s11 = s11;
                                l_s12 = s12;
                                l_s13 = s13;
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                g_s6 = l_s6;
                g_s10 = l_s10;
                g_s11 = l_s11;
                g_s12 = l_s12;
                g_s13 = l_s13;

                int final_shifts[14];
                memcpy(final_shifts, base_shifts, 14 * sizeof(int));
                final_shifts[6] = g_s6;
                final_shifts[10] = g_s10;
                final_shifts[11] = g_s11;
                final_shifts[12] = g_s12;
                final_shifts[13] = g_s13;

                int pt_arr[N];
                eval_shifts(final_shifts, pt_arr);
                for (int i = 0; i < N; i++) g_pt[i] = 'A' + pt_arr[i];
                g_pt[N] = '\0';
                printf("New Best Score: %.4f | Key: %c%c%c%c%c%c%c%c%c%c%c%c%c%c\n",
                       global_best_sc,
                       KRYPTOS[final_shifts[0]], KRYPTOS[final_shifts[1]],
                       KRYPTOS[final_shifts[2]], KRYPTOS[final_shifts[3]],
                       KRYPTOS[final_shifts[4]], KRYPTOS[final_shifts[5]],
                       KRYPTOS[final_shifts[6]], KRYPTOS[final_shifts[7]],
                       KRYPTOS[final_shifts[8]], KRYPTOS[final_shifts[9]],
                       KRYPTOS[final_shifts[10]], KRYPTOS[final_shifts[11]],
                       KRYPTOS[final_shifts[12]], KRYPTOS[final_shifts[13]]);
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("11.88M configurations swept in %.3f s (%.1f M evals/sec)!\n\n",
           elapsed, 11.881376 / elapsed);

    int final_shifts[14];
    memcpy(final_shifts, base_shifts, 14 * sizeof(int));
    final_shifts[6] = g_s6;
    final_shifts[10] = g_s10;
    final_shifts[11] = g_s11;
    final_shifts[12] = g_s12;
    final_shifts[13] = g_s13;

    printf("======================================================================\n");
    printf("FINAL OPTIMAL RESULT\n");
    printf("======================================================================\n");
    printf("Score: %.4f\n", global_best_sc);
    printf("Quagmire III Key: ");
    for (int i = 0; i < 14; i++) printf("%c", KRYPTOS[final_shifts[i]]);
    printf("\nShifts: [");
    for (int i = 0; i < 14; i++) printf("%d%s", final_shifts[i], i==13?"":", ");
    printf("]\n\n");
    printf("Full Plaintext:\n%s\n\n", g_pt);

    printf("Plaintext in 14-char rows:\n");
    for (int r = 0; r < 11; r++) {
        int len = (r == 10) ? 4 : 14;
        char buf[15];
        memcpy(buf, g_pt + r * 14, len);
        buf[len] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}

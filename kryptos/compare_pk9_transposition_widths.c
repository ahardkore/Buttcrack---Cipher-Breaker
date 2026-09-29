#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

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

static inline float eval_width(int W, const int *shifts, int p_sub, const int *perm, int *out_pt) {
    int H = N / W;
    int p1[N];
    for (int t = 0; t < N; t++) {
        int s = shifts[t % p_sub];
        int p_kr = (ct_kr[t] - s + 26) % 26;
        p1[t] = k2std[p_kr];
    }

    int pt[N];
    int idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            pt[idx++] = p1[r * W + perm[c]];
        }
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

    int test_widths[] = {6, 8, 9, 12, 16, 18, 24};
    int n_widths = sizeof(test_widths) / sizeof(test_widths[0]);

    printf("======================================================================\n");
    printf("Comparing Transposition Factor Widths on PK9 (p_sub = 14)\n");
    printf("======================================================================\n\n");

    for (int wi = 0; wi < n_widths; wi++) {
        int W = test_widths[wi];
        int H = N / W;

        float best_score = -999.0f;
        int best_shifts[14];
        int best_perm[32];
        char best_pt[N + 1];

        double t0 = omp_get_wtime();

        #pragma omp parallel
        {
            unsigned int seed = 555 + omp_get_thread_num() * 1111 + W * 101;
            float loc_score = -999.0f;
            int loc_shifts[14];
            int loc_perm[32];
            char loc_pt[N + 1];

            #pragma omp for schedule(dynamic, 10)
            for (int rep = 0; rep < 1000; rep++) {
                int shifts[14];
                for (int i = 0; i < 14; i++) shifts[i] = rand_r(&seed) % 26;

                int perm[32];
                for (int i = 0; i < W; i++) perm[i] = i;
                for (int i = W - 1; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
                }

                float cur_score = eval_width(W, shifts, 14, perm, NULL);
                float temp = 1.5f;
                float cooling = 0.999f;

                for (int step = 0; step < 3000; step++) {
                    int move_type = rand_r(&seed) % 2;
                    if (move_type == 0) {
                        int col = rand_r(&seed) % 14;
                        int old_s = shifts[col];
                        int new_s = (old_s + 1 + (rand_r(&seed) % 25)) % 26;
                        shifts[col] = new_s;
                        float sc = eval_width(W, shifts, 14, perm, NULL);
                        float d = sc - cur_score;
                        if (d > 0.0f || expf(d / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                            cur_score = sc;
                        } else {
                            shifts[col] = old_s;
                        }
                    } else {
                        int c1 = rand_r(&seed) % W;
                        int c2 = rand_r(&seed) % W;
                        if (c1 == c2) continue;
                        int tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;
                        float sc = eval_width(W, shifts, 14, perm, NULL);
                        float d = sc - cur_score;
                        if (d > 0.0f || expf(d / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                            cur_score = sc;
                        } else {
                            perm[c2] = perm[c1]; perm[c1] = tmp;
                        }
                    }
                    temp *= cooling;
                }

                if (cur_score > loc_score) {
                    loc_score = cur_score;
                    memcpy(loc_shifts, shifts, 14 * sizeof(int));
                    memcpy(loc_perm, perm, W * sizeof(int));
                    int pt_arr[N];
                    eval_width(W, shifts, 14, perm, pt_arr);
                    for (int i = 0; i < N; i++) loc_pt[i] = 'A' + pt_arr[i];
                    loc_pt[N] = '\0';
                }
            }

            #pragma omp critical
            {
                if (loc_score > best_score) {
                    best_score = loc_score;
                    memcpy(best_shifts, loc_shifts, 14 * sizeof(int));
                    memcpy(best_perm, loc_perm, W * sizeof(int));
                    strcpy(best_pt, loc_pt);
                }
            }
        }

        double el = omp_get_wtime() - t0;
        printf("Width %2d (Rows %2d): Best Score = %.4f in %.2fs\n", W, H, best_score, el);
        printf("  Key KR: ");
        for (int i = 0; i < 14; i++) printf("%c", KRYPTOS[best_shifts[i]]);
        printf(" | Perm: [");
        for (int i = 0; i < (W < 12 ? W : 12); i++) printf("%d%s", best_perm[i], i == (W < 12 ? W - 1 : 11) ? "" : ", ");
        if (W > 12) printf("...");
        printf("]\n");
        printf("  PT: %.70s...\n\n", best_pt);
    }

    return 0;
}

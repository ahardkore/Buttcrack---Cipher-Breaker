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

const char *Z_STR = "EVIJSAOMWYTEESREOXDVFTIDNMZTOXAEELTGEWSUDEMOTNBSRHEITTFDLERTTOMASEJNAEWAARSENXHEPEEDTEYOLNAEEEHSESEVITEEECFRSDEELEOPPDSEIDINYSEDSAATOEOREWOEKSEN";

static int z_arr[N];

void init_z() {
    for (int i = 0; i < N; i++) {
        z_arr[i] = Z_STR[i] - 'A';
    }
}

// Invert single columnar transposition:
// Given text in 'src' of length N, grid H x W.
// The text was written by rows and read by cols according to perm.
// Inverting: write into columns according to perm, read out by rows.
static inline void invert_columnar(const int *src, int W, const int *perm, int *dst) {
    int H = N / W;
    int idx = 0;
    for (int c_idx = 0; c_idx < W; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < H; r++) {
            dst[r * W + col] = src[idx++];
        }
    }
}

static inline float eval_quad(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

void test_double_columnar_sa(int W1, int W2, int restarts) {
    float global_best_sc = -999.0f;
    int g_p1[32], g_p2[32];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 123 + omp_get_thread_num() * 1777 + W1 * 13 + W2 * 29;
        float loc_best_sc = -999.0f;
        int l_p1[32], l_p2[32];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 25)
        for (int rep = 0; rep < restarts; rep++) {
            int p1[32], p2[32];
            for (int i = 0; i < W1; i++) p1[i] = i;
            for (int i = W1 - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = p1[i]; p1[i] = p1[j]; p1[j] = tmp;
            }
            for (int i = 0; i < W2; i++) p2[i] = i;
            for (int i = W2 - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = p2[i]; p2[i] = p2[j]; p2[j] = tmp;
            }

            int mid[N], pt[N];
            invert_columnar(z_arr, W2, p2, mid);
            invert_columnar(mid, W1, p1, pt);
            float cur_sc = eval_quad(pt);

            float temp = 1.8f;
            float cooling = 0.999f;

            for (int step = 0; step < 3000; step++) {
                int layer = rand_r(&seed) % 2;
                int c1, c2, tmp;

                if (layer == 0) {
                    c1 = rand_r(&seed) % W1;
                    c2 = rand_r(&seed) % W1;
                    if (c1 == c2) continue;
                    tmp = p1[c1]; p1[c1] = p1[c2]; p1[c2] = tmp;
                } else {
                    c1 = rand_r(&seed) % W2;
                    c2 = rand_r(&seed) % W2;
                    if (c1 == c2) continue;
                    tmp = p2[c1]; p2[c1] = p2[c2]; p2[c2] = tmp;
                }

                invert_columnar(z_arr, W2, p2, mid);
                invert_columnar(mid, W1, p1, pt);
                float sc = eval_quad(pt);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    if (layer == 0) { p1[c2] = p1[c1]; p1[c1] = tmp; }
                    else { p2[c2] = p2[c1]; p2[c1] = tmp; }
                }

                temp *= cooling;
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_p1, p1, W1 * sizeof(int));
                memcpy(l_p2, p2, W2 * sizeof(int));

                invert_columnar(z_arr, W2, p2, mid);
                invert_columnar(mid, W1, p1, pt);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_p1, l_p1, W1 * sizeof(int));
                memcpy(g_p2, l_p2, W2 * sizeof(int));
                strcpy(g_pt, l_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Pair (%2d, %2d) [%d restarts, %.2fs]: Best Score = %.4f\n",
           W1, W2, restarts, elapsed, global_best_sc);
    printf("  PT: %.75s...\n\n", g_pt);
}

int main() {
    load_quads();
    init_z();

    printf("======================================================================\n");
    printf("Testing Double Columnar Transposition Configurations on Z (N=144)\n");
    printf("======================================================================\n\n");

    int pairs[][2] = {
        {12, 12},
        {8, 18},
        {18, 8},
        {9, 16},
        {16, 9},
        {6, 24},
        {24, 6}
    };
    int n_pairs = sizeof(pairs) / sizeof(pairs[0]);

    for (int i = 0; i < n_pairs; i++) {
        test_double_columnar_sa(pairs[i][0], pairs[i][1], 5000);
    }

    return 0;
}

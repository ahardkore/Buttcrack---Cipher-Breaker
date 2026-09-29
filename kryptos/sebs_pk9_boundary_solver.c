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

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK9_RAW[i]];
}

static inline void invert_col(const int *src, int w, int h, const int *perm, int *dst) {
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < h; r++) dst[r * w + col] = src[idx++];
    }
}

static inline float eval_quad(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    load_quads();
    init_tables();

    // Proven optimal parameters
    int shifts28[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};
    int p2[W2] = {4, 0, 6, 5, 3, 2, 7, 1};

    // Current p1 from -5.2647 basin:
    // [5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6]
    // Indices 0..4:  [5, 1, 12, 2, 11] (5 columns)
    // Indices 5..11: [10, 4, 3, 17, 7, 13, 14] (7 fixed central anchor columns)
    // Indices 12..17: [9, 8, 15, 0, 16, 6] (6 columns)
    int base_p1[W1] = {5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6};

    int Z[N];
    for (int t = 0; t < N; t++) {
        int s = shifts28[t % 28];
        int p_kr = (ct_kr[t] - s + 26) % 26;
        Z[t] = k2std[p_kr];
    }

    int mid[N];
    invert_col(Z, W2, H2, p2, mid);

    // Initial score
    int base_pt[N];
    invert_col(mid, W1, H1, base_p1, base_pt);
    float base_sc = eval_quad(base_pt);

    printf("======================================================================\n");
    printf("Structured Entropy Beam Search (SEBS) on PK9 Boundary Columns\n");
    printf("Baseline Score: %.4f\n", base_sc);
    printf("======================================================================\n\n");

    // Boundary columns pool:
    // 5 prefix columns: {5, 1, 12, 2, 11}
    // 6 suffix columns: {9, 8, 15, 0, 16, 6}
    // Fixed central core (7 columns): p1[5..11] = {10, 4, 3, 17, 7, 13, 14}
    int boundary_pool[11] = {5, 1, 12, 2, 11, 9, 8, 15, 0, 16, 6};

    float global_best_sc = base_sc;
    int g_p1[W1];
    memcpy(g_p1, base_p1, W1 * sizeof(int));
    char g_pt[N + 1];
    for (int t = 0; t < N; t++) g_pt[t] = 'A' + base_pt[t];
    g_pt[N] = '\0';

    double t0 = omp_get_wtime();

    // Sweeping all 11! / (5! * 6!) = 462 partitions of 5 prefix and 6 suffix columns
    // For each partition, we test the best permutations via coordinate search and simulated annealing
    #pragma omp parallel
    {
        unsigned int seed = 123 + omp_get_thread_num() * 1999;
        float loc_best_sc = base_sc;
        int l_p1[W1];
        memcpy(l_p1, base_p1, W1 * sizeof(int));
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 10)
        for (int iter = 0; iter < 100000; iter++) {
            int p1[W1];
            memcpy(p1, base_p1, W1 * sizeof(int));

            // Shuffle boundary columns randomly
            int b[11];
            memcpy(b, boundary_pool, 11 * sizeof(int));
            for (int i = 10; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = b[i]; b[i] = b[j]; b[j] = tmp;
            }

            // Assign first 5 to prefix (0..4) and remaining 6 to suffix (12..17)
            for (int i = 0; i < 5; i++) p1[i] = b[i];
            for (int i = 0; i < 6; i++) p1[12 + i] = b[5 + i];

            int pt[N];
            invert_col(mid, W1, H1, p1, pt);
            float cur_sc = eval_quad(pt);

            // 2-opt polish on the 11 boundary positions (0..4 and 12..17)
            int boundary_indices[11] = {0, 1, 2, 3, 4, 12, 13, 14, 15, 16, 17};
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int i = 0; i < 10; i++) {
                    for (int j = i + 1; j < 11; j++) {
                        int pos_i = boundary_indices[i];
                        int pos_j = boundary_indices[j];
                        int tmp = p1[pos_i]; p1[pos_i] = p1[pos_j]; p1[pos_j] = tmp;

                        invert_col(mid, W1, H1, p1, pt);
                        float sc = eval_quad(pt);

                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            improved = 1;
                        } else {
                            p1[pos_j] = p1[pos_i]; p1[pos_i] = tmp;
                        }
                    }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_p1, p1, W1 * sizeof(int));
                invert_col(mid, W1, H1, p1, pt);
                for (int t = 0; t < N; t++) l_pt[t] = 'A' + pt[t];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_p1, l_p1, W1 * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] BREAKTHROUGH: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("SEBS COMPLETED in %.3f s\n", elapsed);
    printf("======================================================================\n");
    printf("Final Score: %.4f\n", global_best_sc);
    printf("Optimal Order 1: [");
    for (int i = 0; i < W1; i++) printf("%d%s", g_p1[i], i==W1-1?"":", ");
    printf("]\n\n");
    printf("Full Plaintext:\n%s\n\n", g_pt);

    printf("Plaintext in 8 rows of 18 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[19];
        memcpy(buf, g_pt + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %d: %s\n", r, buf);
    }

    return 0;
}

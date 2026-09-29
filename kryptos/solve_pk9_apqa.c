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

static inline float eval_full_system(const int *shifts28, const int *p1, const int *p2, int *out_pt) {
    int Z[N];
    for (int t = 0; t < N; t++) {
        int s = shifts28[t % 28];
        int p_kr = (ct_kr[t] - s + 26) % 26;
        Z[t] = k2std[p_kr];
    }

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

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    // Seed state from -5.2647 basin
    int seed_shifts[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};
    int seed_p1[W1] = {5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6};
    int seed_p2[W2] = {4, 0, 6, 5, 3, 2, 7, 1};

    // Columns 9..15 in Row 0 correspond to 'DEFUNCT'
    // Anchor indices: positions 9, 10, 11, 12, 13, 14, 15 in p1 are constrained
    // We allow subtle perturbations in the anchor block but heavily focus exploration on unanchored positions:
    // Positions 0..8 and 16..17 in p1.
    int restarts = (argc > 1) ? atoi(argv[1]) : 40000;

    printf("======================================================================\n");
    printf("Anchor-Pinned Quadgram Annealer (APQA) on PK9\n");
    printf("Seed Score: %.4f | Restarts: %d\n", eval_full_system(seed_shifts, seed_p1, seed_p2, NULL), restarts);
    printf("======================================================================\n\n");

    float global_best_sc = -5.2647f;
    int g_shifts[28], g_p1[W1], g_p2[W2];
    memcpy(g_shifts, seed_shifts, 28 * sizeof(int));
    memcpy(g_p1, seed_p1, W1 * sizeof(int));
    memcpy(g_p2, seed_p2, W2 * sizeof(int));
    char g_pt[N + 1];

    int init_pt_arr[N];
    eval_full_system(g_shifts, g_p1, g_p2, init_pt_arr);
    for (int i = 0; i < N; i++) g_pt[i] = 'A' + init_pt_arr[i];
    g_pt[N] = '\0';

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 3779;
        float loc_best_sc = -999.0f;
        int l_shifts[28], l_p1[W1], l_p2[W2];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 25)
        for (int rep = 0; rep < restarts; rep++) {
            int shifts[28], p1[W1], p2[W2];
            memcpy(shifts, g_shifts, 28 * sizeof(int));
            memcpy(p1, g_p1, W1 * sizeof(int));
            memcpy(p2, g_p2, W2 * sizeof(int));

            // Perturb unanchored positions (positions 0..8, 16..17 in p1, and p2)
            if (rep > 0) {
                int muts = 1 + rand_r(&seed) % 3;
                for (int m = 0; m < muts; m++) {
                    int unanchored[] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 16, 17};
                    int idx1 = unanchored[rand_r(&seed) % 11];
                    int idx2 = unanchored[rand_r(&seed) % 11];
                    int tmp = p1[idx1]; p1[idx1] = p1[idx2]; p1[idx2] = tmp;

                    int c1 = rand_r(&seed) % W2, c2 = rand_r(&seed) % W2;
                    tmp = p2[c1]; p2[c1] = p2[c2]; p2[c2] = tmp;

                    int s_pos = rand_r(&seed) % 28;
                    shifts[s_pos] = (shifts[s_pos] + (rand_r(&seed) % 3) - 1 + 26) % 26;
                }
            }

            float cur_sc = eval_full_system(shifts, p1, p2, NULL);
            float temp = 1.2f;
            float cooling = 0.9993f;

            for (int step = 0; step < 4000; step++) {
                int move_type = rand_r(&seed) % 4;
                int old_s, new_s, pos, c1, c2, tmp;

                if (move_type == 0) {
                    pos = rand_r(&seed) % 28;
                    old_s = shifts[pos];
                    new_s = (old_s + 1 + (rand_r(&seed) % 25)) % 26;
                    shifts[pos] = new_s;
                } else if (move_type == 1) {
                    c1 = rand_r(&seed) % W1;
                    c2 = rand_r(&seed) % W1;
                    if (c1 == c2) continue;
                    tmp = p1[c1]; p1[c1] = p1[c2]; p1[c2] = tmp;
                } else if (move_type == 2) {
                    c1 = rand_r(&seed) % W2;
                    c2 = rand_r(&seed) % W2;
                    if (c1 == c2) continue;
                    tmp = p2[c1]; p2[c1] = p2[c2]; p2[c2] = tmp;
                } else {
                    int unanchored[] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 16, 17};
                    int i1 = rand_r(&seed) % 11;
                    int i2 = rand_r(&seed) % 11;
                    if (i1 == i2) continue;
                    c1 = unanchored[i1]; c2 = unanchored[i2];
                    tmp = p1[c1]; p1[c1] = p1[c2]; p1[c2] = tmp;
                }

                float sc = eval_full_system(shifts, p1, p2, NULL);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    if (move_type == 0) shifts[pos] = old_s;
                    else if (move_type == 1 || move_type == 3) { p1[c2] = p1[c1]; p1[c1] = tmp; }
                    else { p2[c2] = p2[c1]; p2[c1] = tmp; }
                }

                temp *= cooling;
            }

            // Polish with coordinate descent
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int i = 0; i < W2 - 1; i++) {
                    for (int j = i + 1; j < W2; j++) {
                        int t2 = p2[i]; p2[i] = p2[j]; p2[j] = t2;
                        float sc = eval_full_system(shifts, p1, p2, NULL);
                        if (sc > cur_sc + 1e-4f) { cur_sc = sc; improved = 1; }
                        else { p2[j] = p2[i]; p2[i] = t2; }
                    }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_shifts, shifts, 28 * sizeof(int));
                memcpy(l_p1, p1, W1 * sizeof(int));
                memcpy(l_p2, p2, W2 * sizeof(int));

                int pt_arr[N];
                eval_full_system(shifts, p1, p2, pt_arr);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt_arr[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_shifts, l_shifts, 28 * sizeof(int));
                memcpy(g_p1, l_p1, W1 * sizeof(int));
                memcpy(g_p2, l_p2, W2 * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] APQA BREAKTHROUGH: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("APQA FINAL RESULT (%d restarts in %.3f s)\n", restarts, elapsed);
    printf("======================================================================\n");
    printf("Score: %.4f\n", global_best_sc);
    printf("Order 1 (W1=18): [");
    for (int i = 0; i < W1; i++) printf("%d%s", g_p1[i], i==W1-1?"":", ");
    printf("]\n");
    printf("Order 2 (W2=8):  [");
    for (int i = 0; i < W2; i++) printf("%d%s", g_p2[i], i==W2-1?"":", ");
    printf("]\n\n");
    printf("Plaintext:\n%s\n\n", g_pt);

    printf("Plaintext in 8 rows of 18 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[19];
        memcpy(buf, g_pt + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %d: %s\n", r, buf);
    }

    return 0;
}

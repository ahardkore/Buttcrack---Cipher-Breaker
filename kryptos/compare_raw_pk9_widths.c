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

static inline float eval_trans(const int *q4, const int *q7, int W, const int *perm, int mode, int *out_pt) {
    int H = N / W;
    int Z[N];
    for (int t = 0; t < N; t++) {
        int ks = (q4[t % 4] + q7[t % 7]) % 26;
        int p_kr = (ct_kr[t] - ks + 26) % 26;
        Z[t] = k2std[p_kr];
    }

    int pt[N];
    if (mode == 0) {
        // Columnar invert: write cols by perm, read by rows
        int idx = 0;
        for (int c_idx = 0; c_idx < W; c_idx++) {
            int col = perm[c_idx];
            for (int r = 0; r < H; r++) pt[r * W + col] = Z[idx++];
        }
    } else {
        // Row perm: read rows with permuted cols
        int idx = 0;
        for (int r = 0; r < H; r++) {
            for (int c = 0; c < W; c++) pt[idx++] = Z[r * W + perm[c]];
        }
    }

    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

void solve_width(int W, int mode, int restarts) {
    float global_best_sc = -999.0f;
    int g_q4[4], g_q7[7], g_perm[32];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 777 + omp_get_thread_num() * 1999 + W * 31;
        float loc_best_sc = -999.0f;
        int l_q4[4], l_q7[7], l_perm[32];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 25)
        for (int rep = 0; rep < restarts; rep++) {
            int q4[4], q7[7], perm[32];
            for (int i = 0; i < 4; i++) q4[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;
            for (int i = 0; i < W; i++) perm[i] = i;
            for (int i = W - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
            }

            float cur_sc = eval_trans(q4, q7, W, perm, mode, NULL);
            float temp = 2.0f;
            float cooling = 0.9991f;

            for (int step = 0; step < 3500; step++) {
                int move_type = rand_r(&seed) % 3;
                int old_v, new_v, pos, c1, c2, tmp;

                if (move_type == 0) {
                    pos = rand_r(&seed) % 4; old_v = q4[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q4[pos] = new_v;
                } else if (move_type == 1) {
                    pos = rand_r(&seed) % 7; old_v = q7[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q7[pos] = new_v;
                } else {
                    c1 = rand_r(&seed) % W; c2 = rand_r(&seed) % W;
                    if (c1 == c2) continue;
                    tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;
                }

                float sc = eval_trans(q4, q7, W, perm, mode, NULL);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    if (move_type == 0) q4[pos] = old_v;
                    else if (move_type == 1) q7[pos] = old_v;
                    else { perm[c2] = perm[c1]; perm[c1] = tmp; }
                }

                temp *= cooling;
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_q4, q4, 4 * sizeof(int));
                memcpy(l_q7, q7, 7 * sizeof(int));
                memcpy(l_perm, perm, W * sizeof(int));

                int pt_arr[N];
                eval_trans(q4, q7, W, perm, mode, pt_arr);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt_arr[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_q4, l_q4, 4 * sizeof(int));
                memcpy(g_q7, l_q7, 7 * sizeof(int));
                memcpy(g_perm, l_perm, W * sizeof(int));
                strcpy(g_pt, l_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Width %2d (Mode %d, %d restarts, %.2fs): Best Score = %.4f\n",
           W, mode, restarts, elapsed, global_best_sc);
    printf("  q4: [%d,%d,%d,%d] q7: [%d,%d,%d,%d,%d,%d,%d]\n",
           g_q4[0], g_q4[1], g_q4[2], g_q4[3],
           g_q7[0], g_q7[1], g_q7[2], g_q7[3], g_q7[4], g_q7[5], g_q7[6]);
    printf("  PT: %.70s...\n\n", g_pt);
}

int main() {
    load_quads();
    init_tables();

    int widths[] = {8, 9, 12, 16, 18};
    int n_widths = 5;

    printf("======================================================================\n");
    printf("Comparing Transposition Factor Widths on RAW PK9 under (q4, q7)\n");
    printf("======================================================================\n");

    for (int i = 0; i < n_widths; i++) {
        solve_width(widths[i], 0, 4000); // Columnar Invert
        solve_width(widths[i], 1, 4000); // Row Perm
    }

    return 0;
}

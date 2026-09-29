#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int ct_std[N];
static int kr_to_std[26];
static int std_to_kr[26];
static float quad_table[26][26][26][26];

void load_models() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) exit(1);
    char q[16]; double cnt; double total = 0;
    while (fscanf(f, "%s %lf", q, &cnt) == 2) if (strlen(q) == 4) total += cnt;
    rewind(f);
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quad_table[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);

    for (int a = 0; a < 26; a++) {
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
}

void decrypt_to_z(int mode, const int *q4, const int *q7, int *z) {
    for (int i = 0; i < N; i++) {
        int sh = (q4[i % 4] + q7[i % 7]) % 26;
        if (mode == 0) z[i] = (ct_std[i] - sh + 26) % 26;
        else if (mode == 1) z[i] = (sh - ct_std[i] + 26) % 26;
        else if (mode == 2) {
            int kr_p = (ct_kr[i] - sh + 26) % 26;
            z[i] = kr_to_std[kr_p];
        } else {
            int kr_p = (sh - ct_kr[i] + 26) % 26;
            z[i] = kr_to_std[kr_p];
        }
    }
}

// Invert columnar transposition:
// Given input array in, and column order o:
// Write in into grid column-by-column at column o[c], read row-by-row into out.
static inline void col_decrypt(const int *in, const int *order, int *out) {
    int grid[H][W];
    int idx = 0;
    for (int c_idx = 0; c_idx < W; c_idx++) {
        int col = order[c_idx];
        for (int r = 0; r < H; r++) grid[r][col] = in[idx++];
    }
    idx = 0;
    for (int r = 0; r < H; r++)
        for (int c = 0; c < W; c++) out[idx++] = grid[r][c];
}

static inline float score_quads(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

static inline void mutate_perm(int *p, unsigned int *seed) {
    int r = rand_r(seed) % 100;
    if (r < 40) {
        int a = rand_r(seed) % W, b = rand_r(seed) % W;
        int t = p[a]; p[a] = p[b]; p[b] = t;
    } else if (r < 75) {
        int a = rand_r(seed) % W, b = rand_r(seed) % W;
        if (a > b) { int t = a; a = b; b = t; }
        while (a < b) { int t = p[a]; p[a] = p[b]; p[b] = t; a++; b--; }
    } else {
        int a = rand_r(seed) % W, b = rand_r(seed) % W;
        int val = p[a];
        if (a < b) { for (int k = a; k < b; k++) p[k] = p[k+1]; }
        else { for (int k = a; k > b; k--) p[k] = p[k-1]; }
        p[b] = val;
    }
}

typedef struct {
    int mode;
    double ll;
    int q4[4];
    int q7[7];
} ClockCand;

int main() {
    load_models();
    printf("Models loaded.\nReading top_clocks.csv...\n");

    FILE *f = fopen("top_clocks.csv", "r");
    if (!f) return 1;
    char line[256];
    fgets(line, sizeof(line), f);

    ClockCand cands[2000];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < 2000) {
        ClockCand *c = &cands[count];
        char dummy1[32], dummy2[32], dummy3[32], dummy4[32];
        if (sscanf(line, "%d,%lf,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s,%s,%s,%s",
                   &c->mode, &c->ll,
                   &c->q4[0], &c->q4[1], &c->q4[2], &c->q4[3],
                   &c->q7[0], &c->q7[1], &c->q7[2], &c->q7[3], &c->q7[4], &c->q7[5], &c->q7[6],
                   dummy1, dummy2, dummy3, dummy4) >= 13) {
            count++;
        }
    }
    fclose(f);
    printf("Loaded %d clock candidates.\n", count);

    // Select top 3 from each of the 4 modes (12 candidates total)
    int test_indices[12];
    int t_cnt = 0;
    for (int m = 0; m < 4; m++) {
        int m_found = 0;
        for (int i = 0; i < count && m_found < 3; i++) {
            if (cands[i].mode == m) {
                test_indices[t_cnt++] = i;
                m_found++;
            }
        }
    }

    printf("Executing Deep Simulated Annealing on Double Columnar Transposition across top 12 clock candidates...\n\n");

    for (int t = 0; t < t_cnt; t++) {
        int idx = test_indices[t];
        ClockCand *c = &cands[idx];
        int z[N];
        decrypt_to_z(c->mode, c->q4, c->q7, z);

        float global_best_sc = -999.0f;
        int global_best_o1[W], global_best_o2[W];
        int global_best_pt[N];

        double t0 = omp_get_wtime();

        #pragma omp parallel
        {
            unsigned int seed = 12345 + omp_get_thread_num() * 9999 + t * 777;
            float local_best_sc = -999.0f;
            int local_best_o1[W], local_best_o2[W], local_best_pt[N];

            int cur_o1[W], cur_o2[W], cur_pt[N], mid[N];

            for (int restart = 0; restart < 200; restart++) {
                // Initialize random perms
                for (int i = 0; i < W; i++) { cur_o1[i] = i; cur_o2[i] = i; }
                for (int i = W - 1; i > 0; i--) {
                    int j1 = rand_r(&seed) % (i + 1); int tmp1 = cur_o1[i]; cur_o1[i] = cur_o1[j1]; cur_o1[j1] = tmp1;
                    int j2 = rand_r(&seed) % (i + 1); int tmp2 = cur_o2[i]; cur_o2[i] = cur_o2[j2]; cur_o2[j2] = tmp2;
                }

                col_decrypt(z, cur_o2, mid);
                col_decrypt(mid, cur_o1, cur_pt);
                float cur_sc = score_quads(cur_pt);

                float T = 0.5f;
                float T_min = 0.005f;
                float alpha = 0.9992f;

                for (int step = 0; step < 5000; step++) {
                    int next_o1[W], next_o2[W];
                    memcpy(next_o1, cur_o1, sizeof(next_o1));
                    memcpy(next_o2, cur_o2, sizeof(next_o2));

                    int mutate_which = rand_r(&seed) % 100;
                    if (mutate_which < 45) {
                        mutate_perm(next_o1, &seed);
                    } else if (mutate_which < 90) {
                        mutate_perm(next_o2, &seed);
                    } else {
                        mutate_perm(next_o1, &seed);
                        mutate_perm(next_o2, &seed);
                    }

                    int next_mid[N], next_pt[N];
                    col_decrypt(z, next_o2, next_mid);
                    col_decrypt(next_mid, next_o1, next_pt);
                    float next_sc = score_quads(next_pt);

                    float diff = next_sc - cur_sc;
                    if (diff > 0.0f || expf(diff / T) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = next_sc;
                        memcpy(cur_o1, next_o1, sizeof(cur_o1));
                        memcpy(cur_o2, next_o2, sizeof(cur_o2));

                        if (cur_sc > local_best_sc) {
                            local_best_sc = cur_sc;
                            memcpy(local_best_o1, cur_o1, sizeof(cur_o1));
                            memcpy(local_best_o2, cur_o2, sizeof(cur_o2));
                            memcpy(local_best_pt, next_pt, sizeof(next_pt));
                        }
                    }

                    T *= alpha;
                    if (T < T_min) T = T_min;
                }
            }

            #pragma omp critical
            {
                if (local_best_sc > global_best_sc) {
                    global_best_sc = local_best_sc;
                    memcpy(global_best_o1, local_best_o1, sizeof(global_best_o1));
                    memcpy(global_best_o2, local_best_o2, sizeof(global_best_o2));
                    memcpy(global_best_pt, local_best_pt, sizeof(local_best_pt));
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        char pt_str[N+1];
        for (int k = 0; k < N; k++) pt_str[k] = global_best_pt[k] + 'A';
        pt_str[N] = 0;

        printf("Candidate %2d (Mode %d, LL: %.2f) Best Score: %.4f (Time: %.2fs)\n",
               idx, c->mode, c->ll, global_best_sc, elapsed);
        printf("  o1: ["); for (int i = 0; i < W; i++) printf("%d%s", global_best_o1[i], i==W-1?"":", "); printf("]\n");
        printf("  o2: ["); for (int i = 0; i < W; i++) printf("%d%s", global_best_o2[i], i==W-1?"":", "); printf("]\n");
        printf("  PT: %.100s...\n\n", pt_str);
    }

    return 0;
}

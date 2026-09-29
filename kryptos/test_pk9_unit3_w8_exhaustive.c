#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W 8
#define UNIT 3
#define TOTAL_PERMS 40320

static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Failed to open english_quads.tsv\n"); exit(1); }
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
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int c_idx[N];
static int hpos[256];
static int k_to_std[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = hpos[(unsigned char)PK9_CT[i]];
    }
}

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

void make_mapping(int width, const int *order, int unit, int *mapping) {
    int m = N / unit;
    int r_count = m / width;
    int idx = 0;
    for (int i = 0; i < width; i++) {
        int c = order[i];
        for (int r = 0; r < r_count; r++) {
            int tok = c + r * width;
            for (int u = 0; u < unit; u++) {
                mapping[idx++] = tok * unit + u;
            }
        }
    }
}

float optimize_4_7(const int *mapping, int *best_q4, int *best_q7, char *best_pt_out) {
    int q4[4] = {0, 0, 0, 0};
    int q7[7] = {0, 0, 0, 0, 0, 0, 0};

    int pt[N];
    for (int o = 0; o < N; o++) {
        int sh = (q4[o % 4] + q7[o % 7]) % 26;
        int dec_k = (c_idx[o] - sh + 26) % 26;
        pt[mapping[o]] = k_to_std[dec_k];
    }
    float cur_sc = score_plain(pt);

    int improved = 1;
    int passes = 0;
    while (improved && passes < 6) {
        improved = 0;
        passes++;

        // Optimize q4[1..3]
        for (int j = 1; j < 4; j++) {
            int old_val = q4[j];
            int best_v = old_val;
            float best_s = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == old_val) continue;
                q4[j] = v;
                for (int o = j; o < N; o += 4) {
                    int sh = (q4[j] + q7[o % 7]) % 26;
                    int dec_k = (c_idx[o] - sh + 26) % 26;
                    pt[mapping[o]] = k_to_std[dec_k];
                }
                float s = score_plain(pt);
                if (s > best_s) {
                    best_s = s;
                    best_v = v;
                }
            }
            q4[j] = best_v;
            for (int o = j; o < N; o += 4) {
                int sh = (q4[j] + q7[o % 7]) % 26;
                int dec_k = (c_idx[o] - sh + 26) % 26;
                pt[mapping[o]] = k_to_std[dec_k];
            }
            if (best_v != old_val) {
                cur_sc = best_s;
                improved = 1;
            }
        }

        // Optimize q7[0..6]
        for (int j = 0; j < 7; j++) {
            int old_val = q7[j];
            int best_v = old_val;
            float best_s = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == old_val) continue;
                q7[j] = v;
                for (int o = j; o < N; o += 7) {
                    int sh = (q4[o % 4] + q7[j]) % 26;
                    int dec_k = (c_idx[o] - sh + 26) % 26;
                    pt[mapping[o]] = k_to_std[dec_k];
                }
                float s = score_plain(pt);
                if (s > best_s) {
                    best_s = s;
                    best_v = v;
                }
            }
            q7[j] = best_v;
            for (int o = j; o < N; o += 7) {
                int sh = (q4[o % 4] + q7[j]) % 26;
                int dec_k = (c_idx[o] - sh + 26) % 26;
                pt[mapping[o]] = k_to_std[dec_k];
            }
            if (best_v != old_val) {
                cur_sc = best_s;
                improved = 1;
            }
        }
    }

    if (best_q4) for (int j = 0; j < 4; j++) best_q4[j] = q4[j];
    if (best_q7) for (int j = 0; j < 7; j++) best_q7[j] = q7[j];
    if (best_pt_out) {
        for (int i = 0; i < N; i++) best_pt_out[i] = 'A' + pt[i];
        best_pt_out[N] = '\0';
    }
    return cur_sc;
}

int next_perm(int *arr, int n) {
    int i = n - 2;
    while (i >= 0 && arr[i] >= arr[i+1]) i--;
    if (i < 0) return 0;
    int j = n - 1;
    while (arr[j] <= arr[i]) j--;
    int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    int l = i + 1, r = n - 1;
    while (l < r) {
        tmp = arr[l]; arr[l] = arr[r]; arr[r] = tmp;
        l++; r--;
    }
    return 1;
}

typedef struct {
    float sc;
    int order[W];
    int q4[4];
    int q7[7];
    char pt[N+1];
} Candidate;

int main() {
    load_quadgrams();
    init_tables();

    printf("Generating %d permutations for Width=%d...\n", TOTAL_PERMS, W);
    int (*all_orders)[W] = malloc(TOTAL_PERMS * sizeof(*all_orders));
    int cur_order[W];
    for (int i = 0; i < W; i++) cur_order[i] = i;
    int idx = 0;
    do {
        for (int i = 0; i < W; i++) all_orders[idx][i] = cur_order[i];
        idx++;
    } while (next_perm(cur_order, W));

    printf("Evaluating all %d orders with unit=%d under {4, 7} clocks...\n", TOTAL_PERMS, UNIT);
    Candidate *all_cands = malloc(TOTAL_PERMS * sizeof(Candidate));
    double t0 = omp_get_wtime();

    #pragma omp parallel for schedule(dynamic, 100)
    for (int i = 0; i < TOTAL_PERMS; i++) {
        int mapping[N];
        make_mapping(W, all_orders[i], UNIT, mapping);
        int q4[4], q7[7];
        char pt[N+1];
        float sc = optimize_4_7(mapping, q4, q7, pt);

        all_cands[i].sc = sc;
        for (int k = 0; k < W; k++) all_cands[i].order[k] = all_orders[i][k];
        for (int j = 0; j < 4; j++) all_cands[i].q4[j] = q4[j];
        for (int j = 0; j < 7; j++) all_cands[i].q7[j] = q7[j];
        strcpy(all_cands[i].pt, pt);
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed in %.2f s (%.1f perms/sec)\n", elapsed, TOTAL_PERMS / elapsed);

    // Find top 10
    for (int i = 0; i < 10; i++) {
        int best_j = i;
        for (int j = i + 1; j < TOTAL_PERMS; j++) {
            if (all_cands[j].sc > all_cands[best_j].sc) best_j = j;
        }
        if (best_j != i) {
            Candidate tmp = all_cands[i];
            all_cands[i] = all_cands[best_j];
            all_cands[best_j] = tmp;
        }
        printf("\nRank %d: Score = %.4f\n", i + 1, all_cands[i].sc);
        printf("Order: ");
        for (int k = 0; k < W; k++) printf("%d ", all_cands[i].order[k]);
        printf("\nq4 (KRYPTOS): ");
        for (int j = 0; j < 4; j++) printf("%c", KRYPTOS[all_cands[i].q4[j]]);
        printf(" | q7 (KRYPTOS): ");
        for (int j = 0; j < 7; j++) printf("%c", KRYPTOS[all_cands[i].q7[j]]);
        printf("\nPlaintext: %s\n", all_cands[i].pt);
    }

    free(all_orders);
    free(all_cands);
    return 0;
}

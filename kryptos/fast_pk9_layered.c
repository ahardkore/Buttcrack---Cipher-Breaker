#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144

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

// Compute mapping: mapping[o] = source plaintext position of the o-th transposed char
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

// Optimize shifts for a given mapping and period P via coordinate ascent
float optimize_shifts(int P, const int *mapping, int *best_shifts, char *best_pt_out) {
    int shifts[32];
    for (int j = 0; j < P; j++) shifts[j] = 0;

    int pt[N];
    for (int o = 0; o < N; o++) {
        int dec_k = (c_idx[o] - shifts[o % P] + 26) % 26;
        pt[mapping[o]] = k_to_std[dec_k];
    }
    float cur_sc = score_plain(pt);

    int improved = 1;
    int passes = 0;
    while (improved && passes < 10) {
        improved = 0;
        passes++;
        for (int j = 0; j < P; j++) {
            int old_sh = shifts[j];
            int best_sh = old_sh;
            float best_s = cur_sc;

            for (int sh = 0; sh < 26; sh++) {
                if (sh == old_sh) continue;
                // Temporarily apply sh to all positions with o % P == j
                for (int o = j; o < N; o += P) {
                    int dec_k = (c_idx[o] - sh + 26) % 26;
                    pt[mapping[o]] = k_to_std[dec_k];
                }
                float s = score_plain(pt);
                if (s > best_s) {
                    best_s = s;
                    best_sh = sh;
                }
            }
            if (best_sh != old_sh) {
                shifts[j] = best_sh;
                cur_sc = best_s;
                improved = 1;
            }
            // Ensure pt reflects current shifts[j]
            for (int o = j; o < N; o += P) {
                int dec_k = (c_idx[o] - shifts[j] + 26) % 26;
                pt[mapping[o]] = k_to_std[dec_k];
            }
        }
    }

    if (best_shifts) {
        for (int j = 0; j < P; j++) best_shifts[j] = shifts[j];
    }
    if (best_pt_out) {
        for (int i = 0; i < N; i++) best_pt_out[i] = 'A' + pt[i];
        best_pt_out[N] = '\0';
    }
    return cur_sc;
}

// Next permutation helper
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

void test_exhaustive(int width, int unit, int P) {
    int total_perms = 1;
    for (int i = 1; i <= width; i++) total_perms *= i;

    printf("\n=== Testing Exhaustive: Width=%d, Unit=%d, Period=%d (Total perms: %d) ===\n",
           width, unit, P, total_perms);

    int (*all_orders)[16] = malloc(total_perms * sizeof(*all_orders));
    int cur_order[16];
    for (int i = 0; i < width; i++) cur_order[i] = i;
    int idx = 0;
    do {
        for (int i = 0; i < width; i++) all_orders[idx][i] = cur_order[i];
        idx++;
    } while (next_perm(cur_order, width));

    float global_best = -999.0f;
    int best_order[16];
    int best_shifts[32];
    char best_pt[N+1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best = -999.0f;
        int local_best_order[16];
        int local_best_shifts[32];
        char local_best_pt[N+1];

        #pragma omp for schedule(dynamic, 100)
        for (int p_idx = 0; p_idx < total_perms; p_idx++) {
            int mapping[N];
            make_mapping(width, all_orders[p_idx], unit, mapping);

            int shifts[32];
            char pt[N+1];
            float sc = optimize_shifts(P, mapping, shifts, pt);

            if (sc > local_best) {
                local_best = sc;
                for (int i = 0; i < width; i++) local_best_order[i] = all_orders[p_idx][i];
                for (int j = 0; j < P; j++) local_best_shifts[j] = shifts[j];
                strcpy(local_best_pt, pt);
            }
        }

        #pragma omp critical
        {
            if (local_best > global_best) {
                global_best = local_best;
                for (int i = 0; i < width; i++) best_order[i] = local_best_order[i];
                for (int j = 0; j < P; j++) best_shifts[j] = local_best_shifts[j];
                strcpy(best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed in %.2f s (%.1f perms/sec)\n", elapsed, total_perms / elapsed);
    printf("Best score: %.4f\n", global_best);
    printf("Best order: ");
    for (int i = 0; i < width; i++) printf("%d ", best_order[i]);
    printf("\nBest shifts (KRYPTOS): ");
    for (int j = 0; j < P; j++) printf("%c", KRYPTOS[best_shifts[j]]);
    printf("\nBest Plaintext: %s\n", best_pt);

    free(all_orders);
}

int main() {
    load_quadgrams();
    init_tables();

    // 1. Unit = 1 (single letters)
    test_exhaustive(6, 1, 7);
    test_exhaustive(8, 1, 7);

    // 2. Unit = 3 (trigraph blocks)
    test_exhaustive(4, 3, 7);
    test_exhaustive(6, 3, 7);
    test_exhaustive(8, 3, 7);

    // 3. Period 12
    test_exhaustive(6, 1, 12);
    test_exhaustive(6, 3, 12);

    return 0;
}

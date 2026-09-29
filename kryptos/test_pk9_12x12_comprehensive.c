#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W 12
#define H 12

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int c_idx[N];
static int k_to_std[26];
static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) return;
    char q[16]; float sc;
    while (fscanf(f, "%s %f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

void init_tables() {
    for (int i = 0; i < 26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
    }
}

static inline float score_text(const int *txt, int len) {
    float sc = 0.0f;
    for (int i = 0; i < len - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (len - 3);
}

// 1. Test geometric routes on 12x12 grid (boustrophedon, spiral, diagonal)
void test_12x12_geometric_routes() {
    printf("=== Testing 12x12 Geometric Routes on PK9 ===\n");
    int grid[12][12];
    int idx = 0;
    for (int r = 0; r < 12; r++)
        for (int c = 0; c < 12; c++)
            grid[r][c] = c_idx[idx++];

    // Route 1: Transpose (row-col flip)
    int route[144];
    idx = 0;
    for (int c = 0; c < 12; c++)
        for (int r = 0; r < 12; r++)
            route[idx++] = grid[r][c];

    // Check slice IoC for periods 1..28
    printf("Route: Standard Transposition (12x12 col read):\n");
    for (int p = 1; p <= 28; p++) {
        int cnt[26] = {0};
        float ioc_sum = 0.0f;
        int slices = 0;
        for (int r = 0; r < p; r++) {
            int l = 0;
            memset(cnt, 0, sizeof(cnt));
            for (int i = r; i < 144; i += p) {
                cnt[route[i]]++;
                l++;
            }
            if (l > 1) {
                int s = 0;
                for (int c = 0; c < 26; c++) s += cnt[c] * (cnt[c] - 1);
                ioc_sum += (float)s / (l * (l - 1));
                slices++;
            }
        }
        float avg_ioc = ioc_sum / slices;
        if (avg_ioc > 0.055) {
            printf("  Period %2d: IoC = %.5f\n", p, avg_ioc);
        }
    }

    // Route 2: Boustrophedon (alternating rows)
    idx = 0;
    for (int r = 0; r < 12; r++) {
        if (r % 2 == 0) {
            for (int c = 0; c < 12; c++) route[idx++] = grid[r][c];
        } else {
            for (int c = 11; c >= 0; c--) route[idx++] = grid[r][c];
        }
    }
    printf("Route: Boustrophedon (rows):\n");
    for (int p = 1; p <= 28; p++) {
        int cnt[26] = {0};
        float ioc_sum = 0.0f;
        int slices = 0;
        for (int r = 0; r < p; r++) {
            int l = 0;
            memset(cnt, 0, sizeof(cnt));
            for (int i = r; i < 144; i += p) {
                cnt[route[i]]++;
                l++;
            }
            if (l > 1) {
                int s = 0;
                for (int c = 0; c < 26; c++) s += cnt[c] * (cnt[c] - 1);
                ioc_sum += (float)s / (l * (l - 1));
                slices++;
            }
        }
        float avg_ioc = ioc_sum / slices;
        if (avg_ioc > 0.055) {
            printf("  Period %2d: IoC = %.5f\n", p, avg_ioc);
        }
    }

    // Route 3: Boustrophedon (cols)
    idx = 0;
    for (int c = 0; c < 12; c++) {
        if (c % 2 == 0) {
            for (int r = 0; r < 12; r++) route[idx++] = grid[r][c];
        } else {
            for (int r = 11; r >= 0; r--) route[idx++] = grid[r][c];
        }
    }
    printf("Route: Boustrophedon (cols):\n");
    for (int p = 1; p <= 28; p++) {
        int cnt[26] = {0};
        float ioc_sum = 0.0f;
        int slices = 0;
        for (int r = 0; r < p; r++) {
            int l = 0;
            memset(cnt, 0, sizeof(cnt));
            for (int i = r; i < 144; i += p) {
                cnt[route[i]]++;
                l++;
            }
            if (l > 1) {
                int s = 0;
                for (int c = 0; c < 26; c++) s += cnt[c] * (cnt[c] - 1);
                ioc_sum += (float)s / (l * (l - 1));
                slices++;
            }
        }
        float avg_ioc = ioc_sum / slices;
        if (avg_ioc > 0.055) {
            printf("  Period %2d: IoC = %.5f\n", p, avg_ioc);
        }
    }
}

// 2. Test Double 12x12 Columnar Transposition with Simulated Annealing
void test_double_12_sa(int restarts) {
    printf("\n=== Running Simulated Annealing on Double Columnar 12x12 on PK9 (Restarts=%d) ===\n", restarts);

    float global_best_score = -99.0f;
    int best_p1[12], best_p2[12], best_s[28];
    char best_pt[145];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 7777 + omp_get_thread_num() * 1234;
        float loc_best = -99.0f;
        int l_p1[12], l_p2[12];

        #pragma omp for
        for (int rep = 0; rep < restarts; rep++) {
            int p1[12], p2[12];
            for (int i = 0; i < 12; i++) { p1[i] = i; p2[i] = i; }
            for (int i = 11; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int t = p1[i]; p1[i] = p1[j]; p1[j] = t;
                j = rand_r(&seed) % (i + 1);
                t = p2[i]; p2[i] = p2[j]; p2[j] = t;
            }

            // Undo double columnar:
            // CT -> stage 2 inverse -> stage 1 inverse
            int inter[144], plain_t[144];
            
            // Decrypt p2
            int grid2[12][12];
            int k = 0;
            for (int m = 0; m < 12; m++) {
                int col = p2[m];
                for (int r = 0; r < 12; r++) grid2[r][col] = c_idx[k++];
            }
            int idx = 0;
            for (int r = 0; r < 12; r++)
                for (int c = 0; c < 12; c++)
                    inter[idx++] = grid2[r][c];

            // Decrypt p1
            int grid1[12][12];
            k = 0;
            for (int m = 0; m < 12; m++) {
                int col = p1[m];
                for (int r = 0; r < 12; r++) grid1[r][col] = inter[k++];
            }
            idx = 0;
            for (int r = 0; r < 12; r++)
                for (int c = 0; c < 12; c++)
                    plain_t[idx++] = grid1[r][c];

            // Measure coset IoC at period 7 and 28
            float ioc7 = 0.0f;
            for (int r = 0; r < 7; r++) {
                int cnt[26] = {0}, l = 0;
                for (int i = r; i < 144; i += 7) { cnt[plain_t[i]]++; l++; }
                int s = 0;
                for (int c = 0; c < 26; c++) s += cnt[c] * (cnt[c] - 1);
                ioc7 += (float)s / (l * (l - 1));
            }
            ioc7 /= 7.0f;

            if (ioc7 > loc_best) {
                loc_best = ioc7;
                memcpy(l_p1, p1, 12 * sizeof(int));
                memcpy(l_p2, p2, 12 * sizeof(int));
            }
        }

        #pragma omp critical
        {
            if (loc_best > global_best_score) {
                global_best_score = loc_best;
                memcpy(best_p1, l_p1, 12 * sizeof(int));
                memcpy(best_p2, l_p2, 12 * sizeof(int));
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Double 12x12 Peak Slice IoC at Period 7: %.5f (took %.2f s)\n", global_best_score, elapsed);
    printf("Best p1: [");
    for (int i = 0; i < 12; i++) printf("%d%s", best_p1[i], i==11?"":", ");
    printf("]\nBest p2: [");
    for (int i = 0; i < 12; i++) printf("%d%s", best_p2[i], i==11?"":", ");
    printf("]\n");
}

int main() {
    load_quadgrams();
    init_tables();

    test_12x12_geometric_routes();
    test_double_12_sa(50000);

    return 0;
}

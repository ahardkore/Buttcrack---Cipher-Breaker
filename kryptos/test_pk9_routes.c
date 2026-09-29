#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

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

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

// Generate routes: mapping[p] = index in X of plaintext letter p
// If Pipeline A: Plaintext P -> Route T -> X -> Sub(4,7) -> C
// Then X[T(p)] = P[p], so P[p] = X[route[p]].
void generate_route(int route_type, int *route) {
    int grid[H][W];
    int idx = 0;

    switch (route_type) {
        case 0: // Identity (row by row left to right)
            for (int r = 0; r < H; r++)
                for (int c = 0; c < W; c++)
                    grid[r][c] = idx++;
            break;
        case 1: // Boustrophedon rows (serpentine rows)
            for (int r = 0; r < H; r++) {
                if (r % 2 == 0) {
                    for (int c = 0; c < W; c++) grid[r][c] = idx++;
                } else {
                    for (int c = W - 1; c >= 0; c--) grid[r][c] = idx++;
                }
            }
            break;
        case 2: // Column by column (downwards)
            for (int c = 0; c < W; c++)
                for (int r = 0; r < H; r++)
                    grid[r][c] = idx++;
            break;
        case 3: // Boustrophedon columns (serpentine cols)
            for (int c = 0; c < W; c++) {
                if (c % 2 == 0) {
                    for (int r = 0; r < H; r++) grid[r][c] = idx++;
                } else {
                    for (int r = H - 1; r >= 0; r--) grid[r][c] = idx++;
                }
            }
            break;
        case 4: // Spiral clockwise from top-left
            {
                int top = 0, bottom = H - 1, left = 0, right = W - 1;
                while (top <= bottom && left <= right) {
                    for (int c = left; c <= right; c++) grid[top][c] = idx++;
                    top++;
                    for (int r = top; r <= bottom; r++) grid[r][right] = idx++;
                    right--;
                    if (top <= bottom) {
                        for (int c = right; c >= left; c--) grid[bottom][c] = idx++;
                        bottom--;
                    }
                    if (left <= right) {
                        for (int r = bottom; r >= top; r--) grid[r][left] = idx++;
                        left++;
                    }
                }
            }
            break;
        case 5: // Spiral counter-clockwise from top-left
            {
                int top = 0, bottom = H - 1, left = 0, right = W - 1;
                while (top <= bottom && left <= right) {
                    for (int r = top; r <= bottom; r++) grid[r][left] = idx++;
                    left++;
                    for (int c = left; c <= right; c++) grid[bottom][c] = idx++;
                    bottom--;
                    if (left <= right) {
                        for (int r = bottom; r >= top; r--) grid[r][right] = idx++;
                        right--;
                    }
                    if (top <= bottom) {
                        for (int c = right; c >= left; c--) grid[top][c] = idx++;
                        top++;
                    }
                }
            }
            break;
        case 6: // Diagonal zigzag (anti-diagonals)
            for (int sum = 0; sum <= (H - 1) + (W - 1); sum++) {
                if (sum % 2 == 0) {
                    for (int r = 0; r < H; r++) {
                        int c = sum - r;
                        if (c >= 0 && c < W) grid[r][c] = idx++;
                    }
                } else {
                    for (int r = H - 1; r >= 0; r--) {
                        int c = sum - r;
                        if (c >= 0 && c < W) grid[r][c] = idx++;
                    }
                }
            }
            break;
        case 7: // Diagonal unidirectional
            for (int sum = 0; sum <= (H - 1) + (W - 1); sum++) {
                for (int r = 0; r < H; r++) {
                    int c = sum - r;
                    if (c >= 0 && c < W) grid[r][c] = idx++;
                }
            }
            break;
        case 8: // Reverse identity
            for (int r = H - 1; r >= 0; r--)
                for (int c = W - 1; c >= 0; c--)
                    grid[r][c] = idx++;
            break;
        case 9: // Reverse serpentine rows
            for (int r = H - 1; r >= 0; r--) {
                if ((H - 1 - r) % 2 == 0) {
                    for (int c = W - 1; c >= 0; c--) grid[r][c] = idx++;
                } else {
                    for (int c = 0; c < W; c++) grid[r][c] = idx++;
                }
            }
            break;
    }

    // Now route[p] is the cell index (r * W + c) where p was placed
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            int p = grid[r][c];
            route[p] = r * W + c;
        }
    }
}

const char *route_names[] = {
    "Identity (Row-by-Row)",
    "Boustrophedon Rows (Serpentine)",
    "Column-by-Column (Downwards)",
    "Boustrophedon Columns (Serpentine)",
    "Spiral Clockwise (Outer to Inner)",
    "Spiral Counter-Clockwise",
    "Diagonal Zigzag",
    "Diagonal Unidirectional",
    "Reverse Row-by-Row",
    "Reverse Serpentine Rows"
};

int main() {
    init_tables();
    load_quadgrams();

    printf("=== Testing Geometric Routes on PK9 under (Q4 + Q7) ===\n\n");

    int num_routes = sizeof(route_names) / sizeof(route_names[0]);

    for (int r_type = 0; r_type < num_routes; r_type++) {
        int route[N];
        generate_route(r_type, route);

        float best_sc = -999.0f;
        int best_q4[4] = {0}, best_q7[7] = {0};
        char best_pt[N + 1] = "";

        // Run 500 restarts of simulated annealing / coordinate ascent
        #pragma omp parallel
        {
            unsigned int seed = 42 + omp_get_thread_num() * 101 + r_type * 37;
            float local_best_sc = -999.0f;
            int local_best_q4[4] = {0}, local_best_q7[7] = {0};
            char local_pt[N + 1] = "";

            #pragma omp for schedule(dynamic, 10)
            for (int restart = 0; restart < 500; restart++) {
                int q4[4], q7[7];
                for (int i = 0; i < 4; i++) q4[i] = rand_r(&seed) % 26;
                for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;

                int X[N], pt[N];
                for (int i = 0; i < N; i++) {
                    int k = (q4[i % 4] + q7[i % 7]) % 26;
                    X[i] = (c_idx[i] - k + 26) % 26;
                }
                for (int p = 0; p < N; p++) {
                    pt[p] = k_to_std[X[route[p]]];
                }
                float cur_sc = score_plain(pt);

                // Coordinate ascent
                int improved = 1;
                int passes = 0;
                while (improved && passes < 6) {
                    improved = 0;
                    passes++;

                    // Q4
                    for (int j = 0; j < 4; j++) {
                        int old_v = q4[j];
                        int best_v = old_v;
                        float best_s = cur_sc;

                        for (int v = 0; v < 26; v++) {
                            if (v == old_v) continue;
                            q4[j] = v;
                            for (int i = 0; i < N; i++) {
                                int k = (q4[i % 4] + q7[i % 7]) % 26;
                                X[i] = (c_idx[i] - k + 26) % 26;
                            }
                            for (int p = 0; p < N; p++) {
                                pt[p] = k_to_std[X[route[p]]];
                            }
                            float s = score_plain(pt);
                            if (s > best_s) { best_s = s; best_v = v; }
                        }
                        q4[j] = best_v;
                        if (best_v != old_v) { cur_sc = best_s; improved = 1; }
                    }

                    // Q7
                    for (int j = 0; j < 7; j++) {
                        int old_v = q7[j];
                        int best_v = old_v;
                        float best_s = cur_sc;

                        for (int v = 0; v < 26; v++) {
                            if (v == old_v) continue;
                            q7[j] = v;
                            for (int i = 0; i < N; i++) {
                                int k = (q4[i % 4] + q7[i % 7]) % 26;
                                X[i] = (c_idx[i] - k + 26) % 26;
                            }
                            for (int p = 0; p < N; p++) {
                                pt[p] = k_to_std[X[route[p]]];
                            }
                            float s = score_plain(pt);
                            if (s > best_s) { best_s = s; best_v = v; }
                        }
                        q7[j] = best_v;
                        if (best_v != old_v) { cur_sc = best_s; improved = 1; }
                    }
                }

                if (cur_sc > local_best_sc) {
                    local_best_sc = cur_sc;
                    for (int i = 0; i < 4; i++) local_best_q4[i] = q4[i];
                    for (int i = 0; i < 7; i++) local_best_q7[i] = q7[i];
                    for (int p = 0; p < N; p++) local_pt[p] = 'A' + pt[p];
                    local_pt[N] = '\0';
                }
            }

            #pragma omp critical
            {
                if (local_best_sc > best_sc) {
                    best_sc = local_best_sc;
                    for (int i = 0; i < 4; i++) best_q4[i] = local_best_q4[i];
                    for (int i = 0; i < 7; i++) best_q7[i] = local_best_q7[i];
                    strcpy(best_pt, local_pt);
                }
            }
        }

        printf("Route %2d [%-35s]: Best Score = %.4f\n", r_type, route_names[r_type], best_sc);
        printf("  Q4: [%d, %d, %d, %d] | Q7: [%d, %d, %d, %d, %d, %d, %d]\n",
               best_q4[0], best_q4[1], best_q4[2], best_q4[3],
               best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
        printf("  Plaintext: %.80s...\n\n", best_pt);
    }

    return 0;
}

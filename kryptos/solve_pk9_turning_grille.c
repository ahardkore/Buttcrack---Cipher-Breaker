#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 12
#define TOTAL 144
#define NUM_ORBITS 36

static const char CT[TOTAL + 1] = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static const char KRYPTOS[27] = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const int s13[7] = {0, 2, 9, 10, 10, 6, 7};

static float quad[26][26][26][26];

void load_quadgrams(const char *path) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -10.0f;

    FILE *f = fopen(path, "r");
    if (!f) { printf("Failed to open %s\n", path); exit(1); }
    char line[128];
    double total = 0;
    long long counts[26][26][26][26] = {0};

    while (fgets(line, sizeof(line), f)) {
        char q[5]; long long cnt;
        if (sscanf(line, "%4s %lld", q, &cnt) == 2) {
            int a = q[0] - 'A', b = q[1] - 'A', c = q[2] - 'A', d = q[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                counts[a][b][c][d] = cnt;
                total += cnt;
            }
        }
    }
    fclose(f);

    float log_tot = log10(total);
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    if (counts[a][b][c][d] > 0)
                        quad[a][b][c][d] = log10((double)counts[a][b][c][d]) - log_tot;
                    else
                        quad[a][b][c][d] = -9.5f;
                }
}

typedef struct {
    int r, c;
} Point;

static Point orbits[NUM_ORBITS][4];

void init_orbits() {
    int seen[N][N] = {0};
    int count = 0;
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            if (seen[r][c]) continue;
            Point p = {r, c};
            for (int turn = 0; turn < 4; turn++) {
                orbits[count][turn] = p;
                seen[p.r][p.c] = 1;
                Point next_p = {p.c, N - 1 - p.r};
                p = next_p;
            }
            count++;
        }
    }
}

static int cmp_points(const void *a, const void *b) {
    Point *pa = (Point*)a;
    Point *pb = (Point*)b;
    if (pa->r != pb->r) return pa->r - pb->r;
    return pa->c - pb->c;
}

void decode_grille(const int *ct_grid, const int *state, int *out) {
    Point current[NUM_ORBITS];
    for (int i = 0; i < NUM_ORBITS; i++) {
        current[i] = orbits[i][state[i]];
    }

    int idx = 0;
    for (int turn = 0; turn < 4; turn++) {
        Point sorted_pts[NUM_ORBITS];
        memcpy(sorted_pts, current, sizeof(Point) * NUM_ORBITS);
        qsort(sorted_pts, NUM_ORBITS, sizeof(Point), cmp_points);

        for (int i = 0; i < NUM_ORBITS; i++) {
            out[idx++] = ct_grid[sorted_pts[i].r * N + sorted_pts[i].c];
        }

        for (int i = 0; i < NUM_ORBITS; i++) {
            Point p = current[i];
            Point next_p = {p.c, N - 1 - p.r};
            current[i] = next_p;
        }
    }
}

static inline float score_text(const int *txt, int n) {
    float sc = 0.0f;
    for (int i = 0; i < n - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (n - 3);
}

int main() {
    load_quadgrams("/home/user/buttcrack/src/buttcrack/data/english_quadgrams.txt");
    init_orbits();

    int top_masks[] = {0, 2, 1, 8, 3, 10, 9, 32, 16, 18, 34, 11, 17, 19, 33, 24};
    int num_masks = sizeof(top_masks) / sizeof(top_masks[0]);

    printf("=== Testing 12x12 Turning Grille on PK9 Candidate Streams ===\n");

    for (int m_idx = 0; m_idx < num_masks; m_idx++) {
        int mask = top_masks[m_idx];
        int shifts[7];
        for (int i = 0; i < 7; i++) shifts[i] = s13[i] + ((mask & (1 << i)) ? 13 : 0);

        int z_num[TOTAL];
        for (int i = 0; i < TOTAL; i++) {
            const char *p = strchr(KRYPTOS, CT[i]);
            int c_idx = p ? (int)(p - KRYPTOS) : 0;
            int z_idx = (c_idx - shifts[i % 7]) % 26;
            if (z_idx < 0) z_idx += 26;
            z_num[i] = KRYPTOS[z_idx] - 'A';
        }

        float global_best = -999.0f;
        int best_state[NUM_ORBITS];
        char best_pt[TOTAL + 1];

        #pragma omp parallel
        {
            unsigned int seed = 42 + omp_get_thread_num() * 10007 + mask * 53;
            int loc_state[NUM_ORBITS], best_loc[NUM_ORBITS], loc_plain[TOTAL];
            float loc_best = -999.0f;

            #pragma omp for schedule(dynamic, 1)
            for (int r = 0; r < 32; r++) {
                for (int i = 0; i < NUM_ORBITS; i++) loc_state[i] = rand_r(&seed) % 4;
                decode_grille(z_num, loc_state, loc_plain);
                float cur_sc = score_text(loc_plain, TOTAL);
                float max_sc = cur_sc;
                memcpy(best_loc, loc_state, sizeof(int)*NUM_ORBITS);

                for (int it = 0; it < 15000; it++) {
                    float temp = 0.3f * (1.0f - (float)it / 15000) + 0.001f;
                    int orb = rand_r(&seed) % NUM_ORBITS;
                    int old_val = loc_state[orb];
                    loc_state[orb] = (old_val + 1 + (rand_r(&seed) % 3)) % 4;

                    decode_grille(z_num, loc_state, loc_plain);
                    float sc = score_text(loc_plain, TOTAL);
                    float diff = sc - cur_sc;

                    if (diff >= 0 || ((float)rand_r(&seed)/RAND_MAX) < expf(diff / temp)) {
                        cur_sc = sc;
                        if (sc > max_sc) {
                            max_sc = sc;
                            memcpy(best_loc, loc_state, sizeof(int)*NUM_ORBITS);
                        }
                    } else {
                        loc_state[orb] = old_val;
                    }
                }

                // Polish
                memcpy(loc_state, best_loc, sizeof(int)*NUM_ORBITS);
                int imp = 1;
                while (imp) {
                    imp = 0;
                    for (int i = 0; i < NUM_ORBITS; i++) {
                        int orig = loc_state[i];
                        for (int v = 0; v < 4; v++) {
                            if (v == orig) continue;
                            loc_state[i] = v;
                            decode_grille(z_num, loc_state, loc_plain);
                            float sc = score_text(loc_plain, TOTAL);
                            if (sc > max_sc + 1e-4f) {
                                max_sc = sc;
                                best_loc[i] = v;
                                orig = v;
                                imp = 1;
                            }
                        }
                        loc_state[i] = orig;
                    }
                }

                if (max_sc > loc_best) {
                    loc_best = max_sc;
                    memcpy(best_loc, loc_state, sizeof(int)*NUM_ORBITS);
                }
            }

            #pragma omp critical
            {
                if (loc_best > global_best) {
                    global_best = loc_best;
                    memcpy(best_state, best_loc, sizeof(int)*NUM_ORBITS);
                }
            }
        }

        int plain[TOTAL];
        decode_grille(z_num, best_state, plain);
        for (int i = 0; i < TOTAL; i++) best_pt[i] = 'A' + plain[i]; best_pt[TOTAL] = '\0';
        printf("Mask %2d: Best Score = %.4f | PT: %.50s...\n", mask, global_best, best_pt);
        fflush(stdout);
    }

    return 0;
}

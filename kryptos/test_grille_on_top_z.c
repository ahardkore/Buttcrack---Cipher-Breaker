#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 12
#define TOTAL 144
#define NUM_ORBITS 36

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

typedef struct { int r, c; } Point;
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

static char Z_cands[16][150];
static int num_cands = 0;

void load_top_z() {
    FILE *f = fopen("top_Z_candidates.txt", "r");
    if (!f) return;
    char line[512];
    while (fgets(line, sizeof(line), f) && num_cands < 10) {
        float dot; int q4[4], q7[7]; char z[150];
        if (sscanf(line, "%f %d %d %d %d %d %d %d %d %d %d %d %s",
                   &dot, &q4[0], &q4[1], &q4[2], &q4[3],
                   &q7[0], &q7[1], &q7[2], &q7[3], &q7[4], &q7[5], &q7[6], z) == 13) {
            strcpy(Z_cands[num_cands++], z);
        }
    }
    fclose(f);
}

int main() {
    load_quadgrams();
    init_orbits();
    load_top_z();

    printf("Testing Fleissner Turning Grilles on %d top Z candidates...\n", num_cands);

    for (int c_idx = 0; c_idx < num_cands; c_idx++) {
        const char *Z = Z_cands[c_idx];
        int z_num[TOTAL];
        for (int i = 0; i < TOTAL; i++) z_num[i] = Z[i] - 'A';

        float cand_best = -999.0f;
        char cand_best_pt[150] = "";

        #pragma omp parallel
        {
            unsigned int seed = 1234 + omp_get_thread_num() * 777 + c_idx * 31;
            int loc_state[NUM_ORBITS], best_loc[NUM_ORBITS], loc_plain[TOTAL];
            float loc_best = -999.0f;

            #pragma omp for schedule(dynamic, 1)
            for (int r = 0; r < 50; r++) {
                for (int i = 0; i < NUM_ORBITS; i++) loc_state[i] = rand_r(&seed) % 4;
                decode_grille(z_num, loc_state, loc_plain);
                float cur_sc = score_text(loc_plain, TOTAL);
                float max_sc = cur_sc;
                memcpy(best_loc, loc_state, sizeof(int)*NUM_ORBITS);

                for (int it = 0; it < 12000; it++) {
                    float temp = 0.5f * (1.0f - (float)it / 12000) + 0.005f;
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

                if (max_sc > loc_best) {
                    loc_best = max_sc;
                }
            }

            #pragma omp critical
            {
                if (loc_best > cand_best) {
                    cand_best = loc_best;
                    decode_grille(z_num, best_loc, loc_plain);
                    for (int i = 0; i < TOTAL; i++) cand_best_pt[i] = 'A' + loc_plain[i];
                    cand_best_pt[TOTAL] = '\0';
                }
            }
        }

        printf("Candidate %d: Best score = %6.4f | %s\n", c_idx, cand_best, cand_best_pt);
    }

    return 0;
}

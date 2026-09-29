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
    if (!f) exit(1);
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

// Candidate 1 (dot 8.0135)
static const char *Z1 = "VTNWCSTYVVOVISENZXAVVTOSQMSKJSEMHJPWDLASHEYGXNOSEHREOTNSYNOEATLLOOLTEEAIRRPEPXTATEMSINSFQMSUDOILISUTCTBEUCYWADMAYNCDSCOUHTJTSSUMKATTIEUWFWFAEHIK";

int main() {
    load_quadgrams();
    init_orbits();

    int z_num[TOTAL];
    for (int i = 0; i < TOTAL; i++) z_num[i] = Z1[i] - 'A';

    printf("Deep Turning Grille Annealing on Z1 (dot 8.0135)...\n");

    float global_best = -999.0f;
    char global_pt[150] = "";

    #pragma omp parallel
    {
        unsigned int seed = 9999 + omp_get_thread_num() * 12345;
        int loc_state[NUM_ORBITS], best_loc[NUM_ORBITS], loc_plain[TOTAL];
        float loc_best = -999.0f;

        #pragma omp for schedule(dynamic, 10)
        for (int r = 0; r < 2000; r++) {
            for (int i = 0; i < NUM_ORBITS; i++) loc_state[i] = rand_r(&seed) % 4;
            decode_grille(z_num, loc_state, loc_plain);
            float cur_sc = score_text(loc_plain, TOTAL);
            float max_sc = cur_sc;
            memcpy(best_loc, loc_state, sizeof(int)*NUM_ORBITS);

            float temp = 0.6f;
            float cooling = 0.9998f;

            for (int it = 0; it < 35000 && temp > 0.001f; it++) {
                temp *= cooling;
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
            if (loc_best > global_best) {
                global_best = loc_best;
                decode_grille(z_num, best_loc, loc_plain);
                for (int i = 0; i < TOTAL; i++) global_pt[i] = 'A' + loc_plain[i];
                global_pt[TOTAL] = '\0';
                printf("New Best: sc = %6.4f | %s\n", global_best, global_pt);
            }
        }
    }

    printf("Deep search finished. Best sc = %6.4f | %s\n", global_best, global_pt);
    return 0;
}

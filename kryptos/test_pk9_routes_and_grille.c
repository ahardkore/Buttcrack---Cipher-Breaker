#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

static float quad[26][26][26][26];

void load_quadgrams() {
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

static inline float score_text(const char *pt, int len) {
    float sc = 0;
    for (int i = 0; i < len - 3; i++) {
        int a = pt[i] - 'A', b = pt[i+1] - 'A', c = pt[i+2] - 'A', d = pt[i+3] - 'A';
        sc += quad[a][b][c][d];
    }
    return sc / (len - 3);
}

// 12 candidate Z streams
static char Z_cands[16][150];
static int num_cands = 0;

void load_top_z() {
    FILE *f = fopen("top_Z_candidates.txt", "r");
    if (!f) return;
    char line[512];
    while (fgets(line, sizeof(line), f) && num_cands < 16) {
        float dot; int q4[4], q7[7]; char z[150];
        if (sscanf(line, "%f %d %d %d %d %d %d %d %d %d %d %d %s",
                   &dot, &q4[0], &q4[1], &q4[2], &q4[3],
                   &q7[0], &q7[1], &q7[2], &q7[3], &q7[4], &q7[5], &q7[6], z) == 13) {
            strcpy(Z_cands[num_cands++], z);
        }
    }
    fclose(f);
}

// Route Transpositions
void test_routes(const char *Z, int cand_idx) {
    char grid[12][12];
    for (int r = 0; r < 12; r++)
        for (int c = 0; c < 12; c++)
            grid[r][c] = Z[r * 12 + c];

    char pt[150];
    pt[144] = '\0';

    // 1. Column-by-column
    int p = 0;
    for (int c = 0; c < 12; c++)
        for (int r = 0; r < 12; r++)
            pt[p++] = grid[r][c];
    float sc = score_text(pt, 144);
    if (sc > -5.2f) printf("Route Col-by-Col cand %d: sc=%6.4f | %s\n", cand_idx, sc, pt);

    // 2. Reverse row snake (boustrophedon)
    p = 0;
    for (int r = 0; r < 12; r++) {
        if (r % 2 == 0) for (int c = 0; c < 12; c++) pt[p++] = grid[r][c];
        else for (int c = 11; c >= 0; c--) pt[p++] = grid[r][c];
    }
    sc = score_text(pt, 144);
    if (sc > -5.2f) printf("Route Snake Row cand %d: sc=%6.4f | %s\n", cand_idx, sc, pt);

    // 3. Reverse col snake
    p = 0;
    for (int c = 0; c < 12; c++) {
        if (c % 2 == 0) for (int r = 0; r < 12; r++) pt[p++] = grid[r][c];
        else for (int r = 11; r >= 0; r--) pt[p++] = grid[r][c];
    }
    sc = score_text(pt, 144);
    if (sc > -5.2f) printf("Route Snake Col cand %d: sc=%6.4f | %s\n", cand_idx, sc, pt);

    // 4. Spiral Inwards Clockwise
    p = 0;
    int top = 0, bottom = 11, left = 0, right = 11;
    while (top <= bottom && left <= right) {
        for (int c = left; c <= right; c++) pt[p++] = grid[top][c];
        top++;
        for (int r = top; r <= bottom; r++) pt[p++] = grid[r][right];
        right--;
        if (top <= bottom) {
            for (int c = right; c >= left; c--) pt[p++] = grid[bottom][c];
            bottom--;
        }
        if (left <= right) {
            for (int r = bottom; r >= top; r--) pt[p++] = grid[r][left];
            left++;
        }
    }
    sc = score_text(pt, 144);
    if (sc > -5.2f) printf("Route Spiral CW cand %d: sc=%6.4f | %s\n", cand_idx, sc, pt);

    // 5. Spiral Inwards CCW
    p = 0; top = 0; bottom = 11; left = 0; right = 11;
    while (top <= bottom && left <= right) {
        for (int r = top; r <= bottom; r++) pt[p++] = grid[r][left];
        left++;
        for (int c = left; c <= right; c++) pt[p++] = grid[bottom][c];
        bottom--;
        if (left <= right) {
            for (int r = bottom; r >= top; r--) pt[p++] = grid[r][right];
            right--;
        }
        if (top <= bottom) {
            for (int c = right; c >= left; c--) pt[p++] = grid[top][c];
            top++;
        }
    }
    sc = score_text(pt, 144);
    if (sc > -5.2f) printf("Route Spiral CCW cand %d: sc=%6.4f | %s\n", cand_idx, sc, pt);

    // 6. Diagonal (bottom-left to top-right)
    p = 0;
    for (int slice = 0; slice < 23; slice++) {
        int z1 = (slice < 12) ? 0 : slice - 11;
        int z2 = (slice < 12) ? slice : 11;
        for (int j = z1; j <= z2; j++) {
            pt[p++] = grid[slice - j][j];
        }
    }
    sc = score_text(pt, 144);
    if (sc > -5.2f) printf("Route Diag cand %d: sc=%6.4f | %s\n", cand_idx, sc, pt);
}

// Turning Grille (Fleissner Grille) SA
// 36 orbits for 12x12
typedef struct {
    int r[4];
    int c[4];
} Orbit;

static Orbit orbits[36];

void init_orbits() {
    int idx = 0;
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            orbits[idx].r[0] = r;
            orbits[idx].c[0] = c;

            orbits[idx].r[1] = c;
            orbits[idx].c[1] = 11 - r;

            orbits[idx].r[2] = 11 - r;
            orbits[idx].c[2] = 11 - c;

            orbits[idx].r[3] = 11 - c;
            orbits[idx].c[3] = r;
            idx++;
        }
    }
}

void read_grille(const char grid[12][12], const int mask[36], char *pt) {
    int p = 0;
    for (int rot = 0; rot < 4; rot++) {
        for (int i = 0; i < 36; i++) {
            int q = (mask[i] + rot) % 4;
            pt[p++] = grid[orbits[i].r[q]][orbits[i].c[q]];
        }
    }
    pt[144] = '\0';
}

void solve_grille_sa(const char *Z, int cand_idx, int restarts, int steps) {
    char grid[12][12];
    for (int r = 0; r < 12; r++)
        for (int c = 0; c < 12; c++)
            grid[r][c] = Z[r * 12 + c];

    float global_best_sc = -999.0f;
    char global_best_pt[150] = "";

    #pragma omp parallel
    {
        unsigned int seed = 777 + omp_get_thread_num() * 1031 + cand_idx * 17;
        float local_best_sc = -999.0f;
        char local_best_pt[150] = "";

        #pragma omp for schedule(dynamic)
        for (int r = 0; r < restarts; r++) {
            int mask[36];
            for (int i = 0; i < 36; i++) mask[i] = rand_r(&seed) % 4;

            char pt[150];
            read_grille(grid, mask, pt);
            float cur_sc = score_text(pt, 144);
            float best_sc = cur_sc;
            int best_mask[36];
            memcpy(best_mask, mask, sizeof(mask));

            float temp = 6.0f;
            float step = temp / steps;

            for (int s = 0; s < steps; s++) {
                int orbit_idx = rand_r(&seed) % 36;
                int old_q = mask[orbit_idx];
                int new_q = (old_q + 1 + rand_r(&seed) % 3) % 4;
                mask[orbit_idx] = new_q;

                read_grille(grid, mask, pt);
                float new_sc = score_text(pt, 144);
                float delta = new_sc - cur_sc;

                if (delta > 0 || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = new_sc;
                    if (cur_sc > best_sc) {
                        best_sc = cur_sc;
                        memcpy(best_mask, mask, sizeof(mask));
                        if (best_sc > local_best_sc) {
                            local_best_sc = best_sc;
                            strcpy(local_best_pt, pt);
                        }
                    }
                } else {
                    mask[orbit_idx] = old_q;
                }
                temp -= step;
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(global_best_pt, local_best_pt);
            }
        }
    }

    if (global_best_sc > -5.2f) {
        printf("Grille cand %d: sc=%6.4f | %s\n", cand_idx, global_best_sc, global_best_pt);
    }
}

int main() {
    load_quadgrams();
    load_top_z();
    init_orbits();

    printf("Loaded %d candidate Z streams.\n", num_cands);
    printf("1. Testing Geometric Routes...\n");
    for (int i = 0; i < num_cands; i++) {
        test_routes(Z_cands[i], i);
    }

    printf("\n2. Testing Fleissner Turning Grille SA (500 restarts, 4000 steps per cand)...\n");
    for (int i = 0; i < num_cands; i++) {
        solve_grille_sa(Z_cands[i], i, 500, 4000);
    }
    printf("Turning Grille check complete.\n");
    return 0;
}

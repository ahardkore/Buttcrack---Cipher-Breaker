#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W1 18
#define H1 8

static float quad[26][26][26][26];
static unsigned char valid_quad[26][26][26][26];

void load_quads() {
    memset(valid_quad, 0, sizeof(valid_quad));
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
    char q[16]; float sc;
    int cnt = 0;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
                valid_quad[a][b][c][d] = 1;
                cnt++;
            }
        }
    }
    fclose(f);
    printf("Loaded %d valid English quadgrams.\n", cnt);
}

// 18 rows of mid (each is 8 letters)
static const char *mid_rows[18] = {
    "LOMAAAUR", // 0
    "VDAOHRDL", // 1
    "FSAAGCLI", // 2
    "RQSIELBI", // 3
    "EHRLNDAT", // 4
    "DTPYUESS", // 5
    "BOYEDFOO", // 6
    "MBTSEOYF", // 7
    "ORMOMTRN", // 8
    "RRRVESCS", // 9
    "UKYILISA", // 10
    "NWILASOA", // 11
    "AENMQREE", // 12
    "DBIESEHS", // 13
    "CJAEYAMU", // 14
    "JRESTIIE", // 15
    "TELBINYO", // 16
    "AMARMTSE"  // 17
};

static int mid_mat[18][8];

void init_mat() {
    for (int r = 0; r < 18; r++) {
        for (int c = 0; c < 8; c++) {
            mid_mat[r][c] = mid_rows[r][c] - 'A';
        }
    }
}

// Objective function with strict defect penalty:
// Every floor quadgram adds a penalty of -20.0
static inline float score_perm_strict(const int *p, int *out_defects) {
    float total = 0.0f;
    int defects = 0;

    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 15; c++) {
            int a = mid_mat[p[c]][r];
            int b = mid_mat[p[c+1]][r];
            int k = mid_mat[p[c+2]][r];
            int d = mid_mat[p[c+3]][r];

            if (valid_quad[a][b][k][d]) {
                total += quad[a][b][k][d];
            } else {
                total += -20.0f; // Strict defect penalty
                defects++;
            }
        }
    }
    if (out_defects) *out_defects = defects;
    return total / (8 * 15);
}

int main(int argc, char **argv) {
    load_quads();
    init_mat();

    int restarts = (argc > 1) ? atoi(argv[1]) : 50000;

    printf("======================================================================\n");
    printf("PK9 Strict Defect-Penalized Search on 18 Columns (Restarts: %d)\n", restarts);
    printf("Total 4-grams per state: 120 (8 rows x 15 positions)\n");
    printf("======================================================================\n\n");

    float global_best_sc = -999.0f;
    int global_min_defects = 120;
    int best_p[18];

    // Seed from our known best
    const int init_p[18] = {15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 14, 16, 8};

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 55555 + omp_get_thread_num() * 1111;
        float loc_best = -999.0f;
        int loc_min_def = 120;
        int loc_p[18];

        #pragma omp for schedule(dynamic, 10)
        for (int rep = 0; rep < restarts; rep++) {
            int p[18];
            if (rep == 0) {
                memcpy(p, init_p, 18 * sizeof(int));
            } else if (rand_r(&seed) % 2 == 0) {
                memcpy(p, init_p, 18 * sizeof(int));
                int swaps = 1 + rand_r(&seed) % 3;
                for (int s = 0; s < swaps; s++) {
                    int a = rand_r(&seed) % 18, b = rand_r(&seed) % 18;
                    int t = p[a]; p[a] = p[b]; p[b] = t;
                }
            } else {
                for (int i = 0; i < 18; i++) p[i] = i;
                for (int i = 17; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int t = p[i]; p[i] = p[j]; p[j] = t;
                }
            }

            int cur_def;
            float cur_sc = score_perm_strict(p, &cur_def);
            float temp = 1.0f;
            float cooling = 0.997f;

            for (int step = 0; step < 5000; step++) {
                int move_type = rand_r(&seed) % 3;
                int a = rand_r(&seed) % 18;
                int b = rand_r(&seed) % 18;
                if (a == b) continue;

                int old_p[18];
                memcpy(old_p, p, 18 * sizeof(int));

                if (move_type == 0) {
                    int t = p[a]; p[a] = p[b]; p[b] = t;
                } else if (move_type == 1) {
                    int l = a < b ? a : b, r = a < b ? b : a;
                    while (l < r) {
                        int t = p[l]; p[l] = p[r]; p[r] = t;
                        l++; r--;
                    }
                } else {
                    int l = a < b ? a : b, r = a < b ? b : a;
                    int val = p[l];
                    for (int k = l; k < r; k++) p[k] = p[k+1];
                    p[r] = val;
                }

                int def;
                float sc = score_perm_strict(p, &def);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                    cur_def = def;
                } else {
                    memcpy(p, old_p, 18 * sizeof(int));
                }

                temp *= cooling;
            }

            if (cur_sc > loc_best) {
                loc_best = cur_sc;
                loc_min_def = cur_def;
                memcpy(loc_p, p, 18 * sizeof(int));
            }
        }

        #pragma omp critical
        {
            if (loc_best > global_best_sc) {
                global_best_sc = loc_best;
                global_min_defects = loc_min_def;
                memcpy(best_p, loc_p, 18 * sizeof(int));
                printf("[Thread %d] Record: Score=%.4f | Defects: %d / 120 (%.1f%% valid)\n",
                       omp_get_thread_num(), global_best_sc, global_min_defects,
                       (120 - global_min_defects) / 120.0f * 100.0f);
                printf("  Order: [");
                for (int i = 0; i < 18; i++) printf("%d%s", best_p[i], i==17?"":", ");
                printf("]\n");
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\n======================================================================\n");
    printf("STRICT SEARCH COMPLETED in %.2f s\n", elapsed);
    printf("======================================================================\n");
    printf("Global Best Score: %.4f | Min Defects: %d / 120 (%.1f%% valid)\n",
           global_best_sc, global_min_defects, (120 - global_min_defects) / 120.0f * 100.0f);
    printf("Optimal Order: [");
    for (int i = 0; i < 18; i++) printf("%d%s", best_p[i], i==17?"":", ");
    printf("]\n\nPlaintext layout (8 rows x 18 cols):\n");

    for (int r = 0; r < 8; r++) {
        char buf[19];
        for (int c = 0; c < 18; c++) buf[c] = mid_mat[best_p[c]][r] + 'A';
        buf[18] = '\0';
        printf("  Row %d: %s\n", r, buf);
    }

    return 0;
}

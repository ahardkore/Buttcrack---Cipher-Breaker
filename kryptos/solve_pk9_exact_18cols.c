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

void load_quads() {
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

// Score a permutation of the 18 rows placed as columns in an 8x18 grid
static inline float score_perm(const int *p) {
    float total = 0.0f;
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 15; c++) {
            int a = mid_mat[p[c]][r];
            int b = mid_mat[p[c+1]][r];
            int k = mid_mat[p[c+2]][r];
            int d = mid_mat[p[c+3]][r];
            total += quad[a][b][k][d];
        }
    }
    return total / (8 * 15);
}

int main(int argc, char **argv) {
    load_quads();
    init_mat();

    int restarts = (argc > 1) ? atoi(argv[1]) : 20000;

    printf("======================================================================\n");
    printf("PK9 Deep Permutation Search on 18 Columns (Restarts: %d)\n", restarts);
    printf("======================================================================\n\n");

    float global_best_sc = -999.0f;
    int best_p[18];

    // Seed from our known best
    const int init_p[18] = {15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 14, 16, 8};

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 7777;
        float loc_best = -999.0f;
        int loc_p[18];

        #pragma omp for schedule(dynamic, 10)
        for (int rep = 0; rep < restarts; rep++) {
            int p[18];
            if (rep == 0) {
                memcpy(p, init_p, 18 * sizeof(int));
            } else if (rand_r(&seed) % 3 == 0) {
                memcpy(p, init_p, 18 * sizeof(int));
                // Perturb 2-3 swaps
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

            float cur_sc = score_perm(p);
            float temp = 0.5f;
            float cooling = 0.996f;

            for (int step = 0; step < 4000; step++) {
                int move_type = rand_r(&seed) % 3;
                int a = rand_r(&seed) % 18;
                int b = rand_r(&seed) % 18;
                if (a == b) continue;

                int old_p[18];
                memcpy(old_p, p, 18 * sizeof(int));

                if (move_type == 0) {
                    // Swap
                    int t = p[a]; p[a] = p[b]; p[b] = t;
                } else if (move_type == 1) {
                    // Block reversal (2-opt)
                    int l = a < b ? a : b;
                    int r = a < b ? b : a;
                    while (l < r) {
                        int t = p[l]; p[l] = p[r]; p[r] = t;
                        l++; r--;
                    }
                } else {
                    // Block insertion
                    int l = a < b ? a : b;
                    int r = a < b ? b : a;
                    int val = p[l];
                    for (int k = l; k < r; k++) p[k] = p[k+1];
                    p[r] = val;
                }

                float sc = score_perm(p);
                float delta = sc - cur_sc;
                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    memcpy(p, old_p, 18 * sizeof(int));
                }

                temp *= cooling;
            }

            if (cur_sc > loc_best) {
                loc_best = cur_sc;
                memcpy(loc_p, p, 18 * sizeof(int));
            }
        }

        #pragma omp critical
        {
            if (loc_best > global_best_sc) {
                global_best_sc = loc_best;
                memcpy(best_p, loc_p, 18 * sizeof(int));
                printf("[Thread %d] Record: Score=%.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  Order: [");
                for (int i = 0; i < 18; i++) printf("%d%s", best_p[i], i==17?"":", ");
                printf("]\n");
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\n======================================================================\n");
    printf("SEARCH COMPLETED in %.2f s | Best Score: %.4f\n", elapsed, global_best_sc);
    printf("======================================================================\n");
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

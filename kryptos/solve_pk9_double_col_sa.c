#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
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

const char *Z_BEST = "VTNWCSTYVVOVISENZXAVVTOSQMSKJSEMHJPWDLASHEYGXNOSEHREOTNSYNOEATLLOOLTEEAIRRPEPXTATEMSINSFQMSUDOILISUTCTBEUCYWADMAYNCDSCOUHTJTSSUMKATTIEUWFWFAEHIK";

void apply_double_col(const char *in, char *out, const int *p1, int w1, const int *p2, int w2) {
    int h1 = 144 / w1;
    char mid[145];
    for (int r = 0; r < h1; r++) {
        for (int c = 0; c < w1; c++) {
            mid[r * w1 + c] = in[p1[c] * h1 + r];
        }
    }
    int h2 = 144 / w2;
    for (int r = 0; r < h2; r++) {
        for (int c = 0; c < w2; c++) {
            out[r * w2 + c] = mid[p2[c] * h2 + r];
        }
    }
    out[144] = '\0';
}

void solve_double(int w1, int w2, int restarts, int steps) {
    float global_best_sc = -999.0f;
    char global_best_pt[150] = "";

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 1013 + w1 * 17 + w2 * 31;
        float local_best_sc = -999.0f;
        char local_best_pt[150] = "";

        #pragma omp for schedule(dynamic)
        for (int r = 0; r < restarts; r++) {
            int p1[32], p2[32];
            for (int i = 0; i < w1; i++) p1[i] = i;
            for (int i = 0; i < w2; i++) p2[i] = i;

            for (int i = w1 - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = p1[i]; p1[i] = p1[j]; p1[j] = tmp;
            }
            for (int i = w2 - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = p2[i]; p2[i] = p2[j]; p2[j] = tmp;
            }

            char pt[150];
            apply_double_col(Z_BEST, pt, p1, w1, p2, w2);
            float cur_sc = score_text(pt, 144);
            float best_sc = cur_sc;

            float temp = 8.0f;
            float step = temp / steps;

            for (int s = 0; s < steps; s++) {
                int stage = rand_r(&seed) % 2;
                int *p = (stage == 0) ? p1 : p2;
                int w = (stage == 0) ? w1 : w2;

                int i = rand_r(&seed) % w;
                int j = rand_r(&seed) % w;
                while (i == j) j = rand_r(&seed) % w;

                int tmp = p[i]; p[i] = p[j]; p[j] = tmp;

                apply_double_col(Z_BEST, pt, p1, w1, p2, w2);
                float new_sc = score_text(pt, 144);
                float delta = new_sc - cur_sc;

                if (delta > 0 || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = new_sc;
                    if (cur_sc > best_sc) {
                        best_sc = cur_sc;
                        if (best_sc > local_best_sc) {
                            local_best_sc = best_sc;
                            strcpy(local_best_pt, pt);
                        }
                    }
                } else {
                    tmp = p[i]; p[i] = p[j]; p[j] = tmp;
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

    printf("(%2d, %2d) Peak sc = %6.4f | %s\n", w1, w2, global_best_sc, global_best_pt);
    fflush(stdout);
}

int main() {
    load_quadgrams();
    printf("Starting Double Columnar SA on Z_BEST...\n");

    int geoms[][2] = {
        {12, 12}, {8, 18}, {18, 8}, {9, 16}, {16, 9}, {6, 24}, {24, 6}
    };
    int num_geoms = sizeof(geoms) / sizeof(geoms[0]);

    for (int i = 0; i < num_geoms; i++) {
        solve_double(geoms[i][0], geoms[i][1], 100, 10000);
    }
    return 0;
}

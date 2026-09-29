#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

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

static inline void decrypt_single(const int *ct, int n, int width, const int *order, int *out) {
    int h = n / width;
    int k = 0;
    for (int m = 0; m < width; m++) {
        int col = order[m];
        for (int r = 0; r < h; r++) {
            out[r * width + col] = ct[k++];
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

    const char *z6_str = "ONEEIHTEEIEKWSUAANCENOEOHGFIIHETIIRHTSUWQSFEEHYSIHTRERYRKINEYTEWUSWCAIEESWGSTMLTEIWHUHTTNLEMAREYEAHEMNOEKILLTPEWYLHDHTDNSDMRAYHNOTNOIRAIIHCLMTOEAEDMHVIHTTEKSISORKDHSTTLSEWTTEMDASWUYRTLDESIGTLTERDXEMOEHEASATEYTOHOLHHHNASSATIUWOSTSIHWSLSSHFOEFNTACEEOIDEAROHALYAYETEHGGRPTEOLRIOISNANFEYLESLNEMEOTDASANMTWOHFWTDTIHEOLDH";
    int n = strlen(z6_str);
    int ct[400];
    for (int i = 0; i < n; i++) ct[i] = z6_str[i] - 'A';

    int known_o1[9] = {1,3,0,4,8,2,6,7,5};
    int known_o2[9] = {4,2,8,1,6,7,0,3,5};
    int inter[400], plain[400];
    decrypt_single(ct, n, 9, known_o2, inter);
    decrypt_single(inter, n, 9, known_o1, plain);
    printf("Ground truth score: %.4f\n", score_text(plain, n));

    // Now test SA with multiple restarts
    int restarts = 128;
    int iters = 30000;
    float global_best = -999.0f;
    int best_o1[9], best_o2[9];
    char best_pt[400];

    printf("Running SA on PK6 (9, 9) with %d restarts...\n", restarts);
    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 10007;
        int loc_o1[9], loc_o2[9], loc_inter[400], loc_plain[400];
        float loc_best = -999.0f;
        int loc_best_o1[9], loc_best_o2[9];

        #pragma omp for schedule(dynamic, 1)
        for (int r = 0; r < restarts; r++) {
            for (int i = 0; i < 9; i++) { loc_o1[i] = i; loc_o2[i] = i; }
            for (int i = 8; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = loc_o1[i]; loc_o1[i] = loc_o1[j]; loc_o1[j] = tmp;
            }
            for (int i = 8; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = loc_o2[i]; loc_o2[i] = loc_o2[j]; loc_o2[j] = tmp;
            }

            decrypt_single(ct, n, 9, loc_o2, loc_inter);
            decrypt_single(loc_inter, n, 9, loc_o1, loc_plain);
            float cur_sc = score_text(loc_plain, n);
            float max_sc = cur_sc;
            int max_o1[9], max_o2[9];
            memcpy(max_o1, loc_o1, sizeof(int)*9);
            memcpy(max_o2, loc_o2, sizeof(int)*9);

            for (int it = 0; it < iters; it++) {
                float temp = 0.5f * (1.0f - (float)it / iters) + 0.002f;
                int mut_first = (rand_r(&seed) % 2);
                int *mut_o = mut_first ? loc_o1 : loc_o2;
                int a = rand_r(&seed) % 9;
                int b = rand_r(&seed) % 9;
                if (a == b) continue;
                int tmp = mut_o[a]; mut_o[a] = mut_o[b]; mut_o[b] = tmp;

                decrypt_single(ct, n, 9, loc_o2, loc_inter);
                decrypt_single(loc_inter, n, 9, loc_o1, loc_plain);
                float sc = score_text(loc_plain, n);

                float diff = sc - cur_sc;
                if (diff >= 0 || ((float)rand_r(&seed)/RAND_MAX) < expf(diff / temp)) {
                    cur_sc = sc;
                    if (sc > max_sc) {
                        max_sc = sc;
                        memcpy(max_o1, loc_o1, sizeof(int)*9);
                        memcpy(max_o2, loc_o2, sizeof(int)*9);
                    }
                } else {
                    mut_o[b] = mut_o[a]; mut_o[a] = tmp;
                }
            }

            // Polish 2-opt
            memcpy(loc_o1, max_o1, sizeof(int)*9);
            memcpy(loc_o2, max_o2, sizeof(int)*9);
            int imp = 1;
            while (imp) {
                imp = 0;
                for (int w = 0; w < 2; w++) {
                    int *target = (w == 0) ? loc_o1 : loc_o2;
                    for (int i = 0; i < 9; i++) {
                        for (int j = i + 1; j < 9; j++) {
                            int tmp = target[i]; target[i] = target[j]; target[j] = tmp;
                            decrypt_single(ct, n, 9, loc_o2, loc_inter);
                            decrypt_single(loc_inter, n, 9, loc_o1, loc_plain);
                            float sc = score_text(loc_plain, n);
                            if (sc > max_sc + 1e-4f) {
                                max_sc = sc;
                                imp = 1;
                            } else {
                                target[j] = target[i]; target[i] = tmp;
                            }
                        }
                    }
                }
            }

            if (max_sc > loc_best) {
                loc_best = max_sc;
                memcpy(loc_best_o1, loc_o1, sizeof(int)*9);
                memcpy(loc_best_o2, loc_o2, sizeof(int)*9);
            }
        }

        #pragma omp critical
        {
            if (loc_best > global_best) {
                global_best = loc_best;
                memcpy(best_o1, loc_best_o1, sizeof(int)*9);
                memcpy(best_o2, loc_best_o2, sizeof(int)*9);
            }
        }
    }

    printf("SA finished in %.2f s | Best score: %.4f\n", omp_get_wtime() - t0, global_best);
    decrypt_single(ct, n, 9, best_o2, inter);
    decrypt_single(inter, n, 9, best_o1, plain);
    for (int i = 0; i < n; i++) best_pt[i] = 'A' + plain[i]; best_pt[n] = 0;
    printf("Best PT: %.70s...\n", best_pt);
    printf("o1: "); for (int i = 0; i < 9; i++) printf("%d ", best_o1[i]); printf("\n");
    printf("o2: "); for (int i = 0; i < 9; i++) printf("%d ", best_o2[i]); printf("\n");

    return 0;
}

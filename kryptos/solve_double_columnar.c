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
    if (!f) {
        printf("Failed to open %s\n", path);
        exit(1);
    }
    char line[128];
    double total = 0;
    long long counts[26][26][26][26] = {0};

    while (fgets(line, sizeof(line), f)) {
        char q[5];
        long long cnt;
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
                    if (counts[a][b][c][d] > 0) {
                        quad[a][b][c][d] = log10((double)counts[a][b][c][d]) - log_tot;
                    } else {
                        quad[a][b][c][d] = -9.5f;
                    }
                }
}

// col_decrypt in C
// grid[r][col] = ct[k++]; pt = row by row
static inline void decrypt_single(const int *ct, int n, int width, const int *order, int *out) {
    int h = n / width;
    // out[r * width + col] where col = order[m], ct index is m * h + r
    for (int m = 0; m < width; m++) {
        int col = order[m];
        int base_ct = m * h;
        for (int r = 0; r < h; r++) {
            out[r * width + col] = ct[base_ct + r];
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

typedef struct {
    float score;
    int o1[32];
    int o2[32];
    char text[400];
} Result;

Result run_sa(const int *ct_num, int n, int w1, int w2, int restarts, int iters_per_restart) {
    Result global_best;
    global_best.score = -999.0f;

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 10007;
        int inter[400];
        int plain[400];
        Result local_best;
        local_best.score = -999.0f;

        #pragma omp for schedule(dynamic, 1)
        for (int r = 0; r < restarts; r++) {
            int cur_o1[32], cur_o2[32];
            for (int i = 0; i < w1; i++) cur_o1[i] = i;
            for (int i = 0; i < w2; i++) cur_o2[i] = i;

            // Fisher-Yates shuffle
            for (int i = w1 - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = cur_o1[i]; cur_o1[i] = cur_o1[j]; cur_o1[j] = tmp;
            }
            for (int i = w2 - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = cur_o2[i]; cur_o2[i] = cur_o2[j]; cur_o2[j] = tmp;
            }

            decrypt_single(ct_num, n, w2, cur_o2, inter);
            decrypt_single(inter, n, w1, cur_o1, plain);
            float cur_score = score_text(plain, n);

            float best_sc_this_restart = cur_score;
            int best_o1_this[32], best_o2_this[32];
            memcpy(best_o1_this, cur_o1, sizeof(int) * w1);
            memcpy(best_o2_this, cur_o2, sizeof(int) * w2);

            for (int it = 0; it < iters_per_restart; it++) {
                // Temperature schedule
                float temp = 0.4f * (1.0f - (float)it / iters_per_restart) + 0.001f;

                // Pick which order to mutate
                int mutate_first = (rand_r(&seed) % (w1 + w2)) < w1;
                int a, b;
                if (mutate_first) {
                    a = rand_r(&seed) % w1;
                    b = rand_r(&seed) % w1;
                    if (a == b) continue;
                    int tmp = cur_o1[a]; cur_o1[a] = cur_o1[b]; cur_o1[b] = tmp;
                } else {
                    a = rand_r(&seed) % w2;
                    b = rand_r(&seed) % w2;
                    if (a == b) continue;
                    int tmp = cur_o2[a]; cur_o2[a] = cur_o2[b]; cur_o2[b] = tmp;
                }

                decrypt_single(ct_num, n, w2, cur_o2, inter);
                decrypt_single(inter, n, w1, cur_o1, plain);
                float sc = score_text(plain, n);

                float diff = sc - cur_score;
                if (diff >= 0.0f || ((float)rand_r(&seed) / RAND_MAX) < expf(diff / temp)) {
                    cur_score = sc;
                    if (sc > best_sc_this_restart) {
                        best_sc_this_restart = sc;
                        memcpy(best_o1_this, cur_o1, sizeof(int) * w1);
                        memcpy(best_o2_this, cur_o2, sizeof(int) * w2);
                    }
                } else {
                    // Revert
                    if (mutate_first) {
                        int tmp = cur_o1[a]; cur_o1[a] = cur_o1[b]; cur_o1[b] = tmp;
                    } else {
                        int tmp = cur_o2[a]; cur_o2[a] = cur_o2[b]; cur_o2[b] = tmp;
                    }
                }
            }

            // Polish 2-opt
            memcpy(cur_o1, best_o1_this, sizeof(int) * w1);
            memcpy(cur_o2, best_o2_this, sizeof(int) * w2);
            int improved = 1;
            while (improved) {
                improved = 0;
                // Try all swaps on o1
                for (int i = 0; i < w1; i++) {
                    for (int j = i + 1; j < w1; j++) {
                        int tmp = cur_o1[i]; cur_o1[i] = cur_o1[j]; cur_o1[j] = tmp;
                        decrypt_single(ct_num, n, w2, cur_o2, inter);
                        decrypt_single(inter, n, w1, cur_o1, plain);
                        float sc = score_text(plain, n);
                        if (sc > best_sc_this_restart + 1e-5f) {
                            best_sc_this_restart = sc;
                            improved = 1;
                        } else {
                            cur_o1[j] = cur_o1[i]; cur_o1[i] = tmp;
                        }
                    }
                }
                // Try all swaps on o2
                for (int i = 0; i < w2; i++) {
                    for (int j = i + 1; j < w2; j++) {
                        int tmp = cur_o2[i]; cur_o2[i] = cur_o2[j]; cur_o2[j] = tmp;
                        decrypt_single(ct_num, n, w2, cur_o2, inter);
                        decrypt_single(inter, n, w1, cur_o1, plain);
                        float sc = score_text(plain, n);
                        if (sc > best_sc_this_restart + 1e-5f) {
                            best_sc_this_restart = sc;
                            improved = 1;
                        } else {
                            cur_o2[j] = cur_o2[i]; cur_o2[i] = tmp;
                        }
                    }
                }
            }

            if (best_sc_this_restart > local_best.score) {
                local_best.score = best_sc_this_restart;
                memcpy(local_best.o1, cur_o1, sizeof(int) * w1);
                memcpy(local_best.o2, cur_o2, sizeof(int) * w2);
                decrypt_single(ct_num, n, w2, cur_o2, inter);
                decrypt_single(inter, n, w1, cur_o1, plain);
                for (int i = 0; i < n; i++) local_best.text[i] = 'A' + plain[i];
                local_best.text[n] = '\0';
            }
        }

        #pragma omp critical
        {
            if (local_best.score > global_best.score) {
                global_best = local_best;
            }
        }
    }

    return global_best;
}

int main(int argc, char **argv) {
    load_quadgrams("/home/user/buttcrack/src/buttcrack/data/english_quadgrams.txt");

    // Positive control: PK6
    const char *z6_str = "ONEEIHTEEIEKWSUAANCENOEOHGFIIHETIIRHTSUWQSFEEHYSIHTRERYRKINEFSTTOEHSHNIOOTIRKSEELKDTMHOESKILTFHEEHEIDENROTEUTTTTLREHETTDELOWWCEOSOEWYTTTIHHEAYMNAIWYERODTFMTTOEYEAFTEIHEWHWOSSHGHTOEFGSHSHHEOFRWREAEWEEEYADLSSSHLMSFHTEDTHNDNLRWAKLOHPRTTHNEOODRAIOAUNLSTTAOOUAMTYTRTETMTOETRCEWAKPMEGRLSHNTAESSEKCYAOPANLSIWIDTTTAEIEIRHNSIPFROEMLITW";
    int n6 = strlen(z6_str);
    int ct6[400];
    for (int i = 0; i < n6; i++) ct6[i] = z6_str[i] - 'A';

    printf("Running positive control on PK6 (w1=9, w2=9, 32 restarts, 20000 iters)...\n");
    double t0 = omp_get_wtime();
    Result res6 = run_sa(ct6, n6, 9, 9, 32, 20000);
    printf("PK6 SA finished in %.2f s | Score: %.4f\n", omp_get_wtime() - t0, res6.score);
    printf("PK6 Plaintext: %.70s...\n", res6.text);
    printf("o1: "); for (int i = 0; i < 9; i++) printf("%d ", res6.o1[i]); printf("\n");
    printf("o2: "); for (int i = 0; i < 9; i++) printf("%d ", res6.o2[i]); printf("\n");

    return 0;
}

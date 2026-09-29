#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144

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

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *UNDONE = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

static int ct_kr[N];
static int k2std[26];
static int hpos[256];

static inline float eval_state_p14_w12(const int *shifts, const int *perm, int *out_pt) {
    int p1[N];
    for (int t = 0; t < N; t++) {
        int s = shifts[t % 14];
        int p_kr = (ct_kr[t] - s + 26) % 26;
        p1[t] = k2std[p_kr];
    }

    int pt[N];
    int idx = 0;
    for (int r = 0; r < 12; r++) {
        for (int c = 0; c < 12; c++) {
            pt[idx++] = p1[r * 12 + perm[c]];
        }
    }

    if (out_pt) {
        memcpy(out_pt, pt, N * sizeof(int));
    }

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main(int argc, char **argv) {
    int total_restarts = (argc > 1) ? atoi(argv[1]) : 30000;

    load_quads();
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)UNDONE[i]];
    }

    printf("======================================================================\n");
    printf("Ultra Deep Joint Annealer on PK9 (Period 14 + Width 12, %d restarts)\n", total_restarts);
    printf("======================================================================\n");

    float global_best_score = -6.2522f;
    int global_best_shifts[14] = {8, 2, 7, 7, 9, 2, 21, 5, 14, 13, 5, 10, 8, 21};
    int global_best_perm[12] = {9, 3, 6, 11, 10, 7, 8, 5, 1, 2, 4, 0};
    char global_best_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 999 + omp_get_thread_num() * 3779;
        float loc_best_score = -999.0f;
        int loc_best_shifts[14];
        int loc_best_perm[12];
        char loc_best_pt[N + 1];

        #pragma omp for schedule(dynamic, 25)
        for (int restart = 0; restart < total_restarts; restart++) {
            int shifts[14];
            int perm[12];

            if (restart % 5 == 0) {
                // Seed from best known
                for (int i = 0; i < 14; i++) {
                    shifts[i] = (global_best_shifts[i] + (rand_r(&seed) % 3) - 1 + 26) % 26;
                }
                memcpy(perm, global_best_perm, 12 * sizeof(int));
                // 2 random swaps
                int c1 = rand_r(&seed) % 12, c2 = rand_r(&seed) % 12;
                int tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;
            } else {
                for (int i = 0; i < 14; i++) shifts[i] = rand_r(&seed) % 26;
                for (int i = 0; i < 12; i++) perm[i] = i;
                for (int i = 11; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
                }
            }

            float cur_score = eval_state_p14_w12(shifts, perm, NULL);
            float temp = 2.0f;
            float cooling = 0.9993f;

            for (int step = 0; step < 5000; step++) {
                int move_type = rand_r(&seed) % 2;

                if (move_type == 0) {
                    int col = rand_r(&seed) % 14;
                    int old_s = shifts[col];
                    int new_s = (old_s + 1 + (rand_r(&seed) % 25)) % 26;
                    shifts[col] = new_s;

                    float new_score = eval_state_p14_w12(shifts, perm, NULL);
                    float delta = new_score - cur_score;

                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_score = new_score;
                    } else {
                        shifts[col] = old_s;
                    }
                } else {
                    int c1 = rand_r(&seed) % 12;
                    int c2 = rand_r(&seed) % 12;
                    if (c1 == c2) continue;

                    int tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;
                    float new_score = eval_state_p14_w12(shifts, perm, NULL);
                    float delta = new_score - cur_score;

                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_score = new_score;
                    } else {
                        perm[c2] = perm[c1]; perm[c1] = tmp;
                    }
                }

                temp *= cooling;
            }

            // Greedy Polish with coordinate descent
            int improved = 1;
            while (improved) {
                improved = 0;
                // Shift adjustments
                for (int c = 0; c < 14; c++) {
                    int best_s = shifts[c];
                    float best_delta = 0.0f;
                    int old_s = shifts[c];
                    for (int diff = 1; diff < 26; diff++) {
                        shifts[c] = (old_s + diff) % 26;
                        float sc = eval_state_p14_w12(shifts, perm, NULL);
                        if (sc - cur_score > best_delta) {
                            best_delta = sc - cur_score;
                            best_s = shifts[c];
                        }
                    }
                    if (best_delta > 1e-4f) {
                        shifts[c] = best_s;
                        cur_score += best_delta;
                        improved = 1;
                    } else {
                        shifts[c] = old_s;
                    }
                }
                // Column swaps
                for (int i = 0; i < 11; i++) {
                    for (int j = i + 1; j < 12; j++) {
                        int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
                        float sc = eval_state_p14_w12(shifts, perm, NULL);
                        if (sc > cur_score + 1e-4f) {
                            cur_score = sc;
                            improved = 1;
                        } else {
                            perm[j] = perm[i]; perm[i] = tmp;
                        }
                    }
                }
            }

            if (cur_score > loc_best_score) {
                loc_best_score = cur_score;
                memcpy(loc_best_shifts, shifts, 14 * sizeof(int));
                memcpy(loc_best_perm, perm, 12 * sizeof(int));

                int pt_arr[N];
                eval_state_p14_w12(shifts, perm, pt_arr);
                for (int i = 0; i < N; i++) loc_best_pt[i] = 'A' + pt_arr[i];
                loc_best_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_score > global_best_score) {
                global_best_score = loc_best_score;
                memcpy(global_best_shifts, loc_best_shifts, 14 * sizeof(int));
                memcpy(global_best_perm, loc_best_perm, 12 * sizeof(int));
                strcpy(global_best_pt, loc_best_pt);
                printf("[Thread %d] NEW RECORD: %.4f\n", omp_get_thread_num(), global_best_score);
                printf("  Key KR: ");
                for (int i = 0; i < 14; i++) printf("%c", KRYPTOS[global_best_shifts[i]]);
                printf(" | Perm: [");
                for (int i = 0; i < 12; i++) printf("%d%s", global_best_perm[i], i == 11 ? "" : ", ");
                printf("]\n");
                printf("  PT: %.70s...\n\n", global_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("%d restarts completed in %.3f s (%.1f restarts/sec)!\n\n",
           total_restarts, elapsed, total_restarts / elapsed);

    printf("======================================================================\n");
    printf("FINAL OPTIMAL RESULT (Period 14 + Width 12 Grid)\n");
    printf("======================================================================\n");
    printf("Score: %.4f\n", global_best_score);
    printf("Quagmire III Key: ");
    for (int i = 0; i < 14; i++) printf("%c", KRYPTOS[global_best_shifts[i]]);
    printf("\nColumn Permutation: [");
    for (int i = 0; i < 12; i++) printf("%d%s", global_best_perm[i], i == 11 ? "" : ", ");
    printf("]\n\n");
    printf("Plaintext:\n%s\n\n", global_best_pt);

    printf("Plaintext in 12-char rows:\n");
    for (int r = 0; r < 12; r++) {
        char buf[13];
        memcpy(buf, global_best_pt + r * 12, 12);
        buf[12] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}

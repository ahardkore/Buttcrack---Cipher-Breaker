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

static inline float eval_q4_q7_grid(const int *q4, const int *q7, int W, const int *perm, int *out_pt) {
    int H = N / W;
    int p1[N];
    for (int t = 0; t < N; t++) {
        int ks = (q4[t % 4] + q7[t % 7]) % 26;
        int p_kr = (ct_kr[t] - ks + 26) % 26;
        p1[t] = k2std[p_kr];
    }

    int pt[N];
    int idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            pt[idx++] = p1[r * W + perm[c]];
        }
    }

    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    load_quads();
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)UNDONE[i]];
    }

    int W = 12;
    int H = 12;

    printf("======================================================================\n");
    printf("Joint (q4, q7, Perm12) Simulated Annealing + Deep Polish\n");
    printf("======================================================================\n");

    float global_best_score = -999.0f;
    int global_best_q4[4];
    int global_best_q7[7];
    int global_best_perm[12];
    char global_best_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 7777;
        float loc_best_score = -999.0f;
        int loc_best_q4[4];
        int loc_best_q7[7];
        int loc_best_perm[12];
        char loc_best_pt[N + 1];

        #pragma omp for schedule(dynamic, 10)
        for (int restart = 0; restart < 5000; restart++) {
            int q4[4], q7[7];
            for (int i = 0; i < 4; i++) q4[i] = rand_r(&seed) % 26;
            q7[0] = 0; // gauge fix
            for (int i = 1; i < 7; i++) q7[i] = rand_r(&seed) % 26;

            int perm[12];
            for (int i = 0; i < 12; i++) perm[i] = i;
            for (int i = 11; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
            }

            float cur_score = eval_q4_q7_grid(q4, q7, W, perm, NULL);
            float temp = 1.8f;
            float cooling = 0.999f;

            for (int step = 0; step < 4000; step++) {
                int move_type = rand_r(&seed) % 3;

                if (move_type == 0) { // Mutate q4
                    int pos = rand_r(&seed) % 4;
                    int old_v = q4[pos];
                    int new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q4[pos] = new_v;

                    float sc = eval_q4_q7_grid(q4, q7, W, perm, NULL);
                    float d = sc - cur_score;
                    if (d > 0.0f || expf(d / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_score = sc;
                    } else {
                        q4[pos] = old_v;
                    }
                } else if (move_type == 1) { // Mutate q7
                    int pos = 1 + (rand_r(&seed) % 6); // q7[0]=0 fixed
                    int old_v = q7[pos];
                    int new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q7[pos] = new_v;

                    float sc = eval_q4_q7_grid(q4, q7, W, perm, NULL);
                    float d = sc - cur_score;
                    if (d > 0.0f || expf(d / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_score = sc;
                    } else {
                        q7[pos] = old_v;
                    }
                } else { // Swap columns
                    int c1 = rand_r(&seed) % 12;
                    int c2 = rand_r(&seed) % 12;
                    if (c1 == c2) continue;

                    int tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;
                    float sc = eval_q4_q7_grid(q4, q7, W, perm, NULL);
                    float d = sc - cur_score;
                    if (d > 0.0f || expf(d / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_score = sc;
                    } else {
                        perm[c2] = perm[c1]; perm[c1] = tmp;
                    }
                }

                temp *= cooling;
            }

            // Polish with greedy coordinate descent
            int improved = 1;
            while (improved) {
                improved = 0;
                // q4 adjustments
                for (int c = 0; c < 4; c++) {
                    int best_v = q4[c];
                    float best_d = 0.0f;
                    int old_v = q4[c];
                    for (int diff = 1; diff < 26; diff++) {
                        q4[c] = (old_v + diff) % 26;
                        float sc = eval_q4_q7_grid(q4, q7, W, perm, NULL);
                        if (sc - cur_score > best_d) {
                            best_d = sc - cur_score;
                            best_v = q4[c];
                        }
                    }
                    if (best_d > 1e-4f) {
                        q4[c] = best_v;
                        cur_score += best_d;
                        improved = 1;
                    } else {
                        q4[c] = old_v;
                    }
                }
                // q7 adjustments
                for (int c = 1; c < 7; c++) {
                    int best_v = q7[c];
                    float best_d = 0.0f;
                    int old_v = q7[c];
                    for (int diff = 1; diff < 26; diff++) {
                        q7[c] = (old_v + diff) % 26;
                        float sc = eval_q4_q7_grid(q4, q7, W, perm, NULL);
                        if (sc - cur_score > best_d) {
                            best_d = sc - cur_score;
                            best_v = q7[c];
                        }
                    }
                    if (best_d > 1e-4f) {
                        q7[c] = best_v;
                        cur_score += best_d;
                        improved = 1;
                    } else {
                        q7[c] = old_v;
                    }
                }
                // Column swaps
                for (int i = 0; i < 11; i++) {
                    for (int j = i + 1; j < 12; j++) {
                        int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
                        float sc = eval_q4_q7_grid(q4, q7, W, perm, NULL);
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
                memcpy(loc_best_q4, q4, 4 * sizeof(int));
                memcpy(loc_best_q7, q7, 7 * sizeof(int));
                memcpy(loc_best_perm, perm, 12 * sizeof(int));

                int pt_arr[N];
                eval_q4_q7_grid(q4, q7, W, perm, pt_arr);
                for (int i = 0; i < N; i++) loc_best_pt[i] = 'A' + pt_arr[i];
                loc_best_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_score > global_best_score) {
                global_best_score = loc_best_score;
                memcpy(global_best_q4, loc_best_q4, 4 * sizeof(int));
                memcpy(global_best_q7, loc_best_q7, 7 * sizeof(int));
                memcpy(global_best_perm, loc_best_perm, 12 * sizeof(int));
                strcpy(global_best_pt, loc_best_pt);
                printf("[Thread %d] Global Best: %.4f\n", omp_get_thread_num(), global_best_score);
                printf("  q4: [%d, %d, %d, %d] (%c%c%c%c) | q7: [%d, %d, %d, %d, %d, %d, %d]\n",
                       global_best_q4[0], global_best_q4[1], global_best_q4[2], global_best_q4[3],
                       KRYPTOS[global_best_q4[0]], KRYPTOS[global_best_q4[1]], KRYPTOS[global_best_q4[2]], KRYPTOS[global_best_q4[3]],
                       global_best_q7[0], global_best_q7[1], global_best_q7[2], global_best_q7[3],
                       global_best_q7[4], global_best_q7[5], global_best_q7[6]);
                printf("  Perm: [");
                for (int i = 0; i < 12; i++) printf("%d%s", global_best_perm[i], i == 11 ? "" : ", ");
                printf("]\n");
                printf("  PT: %.70s...\n\n", global_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("5,000 restarts completed in %.3f s!\n\n", elapsed);

    printf("======================================================================\n");
    printf("FINAL (q4, q7, Perm12) OPTIMUM\n");
    printf("======================================================================\n");
    printf("Score: %.4f\n", global_best_score);
    printf("q4: [%d, %d, %d, %d] (%c%c%c%c)\n",
           global_best_q4[0], global_best_q4[1], global_best_q4[2], global_best_q4[3],
           KRYPTOS[global_best_q4[0]], KRYPTOS[global_best_q4[1]], KRYPTOS[global_best_q4[2]], KRYPTOS[global_best_q4[3]]);
    printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n",
           global_best_q7[0], global_best_q7[1], global_best_q7[2], global_best_q7[3],
           global_best_q7[4], global_best_q7[5], global_best_q7[6]);
    printf("Perm: [");
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

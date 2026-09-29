#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int c_idx[N];
static int alpha_to_std[26];
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
    while (fscanf(f, "%s %f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

void init_tables() {
    for (int i = 0; i < 26; i++) alpha_to_std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
}

static inline float eval_state(const int *q4, const int *q7, const int *order, char *out_plain) {
    int X[N];
    for (int i = 0; i < N; i++) {
        int k = (q4[i % 4] + q7[i % 7]) % 26;
        X[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
    }

    int pt[N];
    int idx = 0;
    for (int r = 0; r < 12; r++) {
        for (int c = 0; c < 12; c++) {
            pt[idx++] = X[r * 12 + order[c]];
        }
    }

    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    sc /= (N - 3);

    if (out_plain) {
        for (int i = 0; i < N; i++) out_plain[i] = 'A' + pt[i];
        out_plain[N] = '\0';
    }
    return sc;
}

int main() {
    init_tables();
    load_quadgrams();

    // Baseline seed
    int seed_q4[4] = {16, 23, 22, 18};
    int seed_q7[7] = {10, 19, 17, 25, 16, 18, 10};
    int seed_order[12] = {8, 0, 7, 1, 10, 11, 2, 3, 6, 5, 9, 4};

    char pt[N + 1];
    float init_sc = eval_state(seed_q4, seed_q7, seed_order, pt);
    printf("Initial Base Score = %.4f\n", init_sc);
    for (int r = 0; r < 12; r++) {
        printf("Row %2d: %.12s\n", r, pt + r * 12);
    }

    float global_best_sc = init_sc;
    int best_q4[4], best_q7[7], best_order[12];
    char best_pt[N + 1];

    for (int i = 0; i < 4; i++) best_q4[i] = seed_q4[i];
    for (int i = 0; i < 7; i++) best_q7[i] = seed_q7[i];
    for (int i = 0; i < 12; i++) best_order[i] = seed_order[i];
    strcpy(best_pt, pt);

    printf("\nRunning deep neighborhood search around seed...\n");

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 12345;
        float local_best_sc = init_sc;
        int local_q4[4], local_q7[7], local_order[12];
        char local_pt[N + 1];

        #pragma omp for schedule(dynamic, 10)
        for (int r = 0; r < 20000; r++) {
            int cur_q4[4], cur_q7[7], cur_order[12];
            for (int i = 0; i < 4; i++) cur_q4[i] = seed_q4[i];
            for (int i = 0; i < 7; i++) cur_q7[i] = seed_q7[i];
            for (int i = 0; i < 12; i++) cur_order[i] = seed_order[i];

            // 1-3 random perturbations
            int perts = 1 + rand_r(&seed) % 3;
            for (int p = 0; p < perts; p++) {
                int type = rand_r(&seed) % 3;
                if (type == 0) {
                    // perturb q4
                    int pos = rand_r(&seed) % 4;
                    cur_q4[pos] = (cur_q4[pos] + 1 + rand_r(&seed) % 25) % 26;
                } else if (type == 1) {
                    // perturb q7
                    int pos = rand_r(&seed) % 7;
                    cur_q7[pos] = (cur_q7[pos] + 1 + rand_r(&seed) % 25) % 26;
                } else {
                    // swap 2 columns
                    int i = rand_r(&seed) % 12;
                    int j = rand_r(&seed) % 12;
                    int tmp = cur_order[i]; cur_order[i] = cur_order[j]; cur_order[j] = tmp;
                }
            }

            char temp_pt[N + 1];
            float cur_sc = eval_state(cur_q4, cur_q7, cur_order, temp_pt);

            // Fast simulated annealing
            float T = 2.0f;
            float T_end = 0.05f;
            int steps = 2000;
            float decay = powf(T_end / T, 1.0f / steps);

            for (int s = 0; s < steps; s++) {
                int type = rand_r(&seed) % 3;
                int saved_v, pos, i, j;
                if (type == 0) {
                    pos = rand_r(&seed) % 4;
                    saved_v = cur_q4[pos];
                    cur_q4[pos] = (cur_q4[pos] + 1 + rand_r(&seed) % 25) % 26;
                } else if (type == 1) {
                    pos = rand_r(&seed) % 7;
                    saved_v = cur_q7[pos];
                    cur_q7[pos] = (cur_q7[pos] + 1 + rand_r(&seed) % 25) % 26;
                } else {
                    i = rand_r(&seed) % 12;
                    j = rand_r(&seed) % 12;
                    int tmp = cur_order[i]; cur_order[i] = cur_order[j]; cur_order[j] = tmp;
                }

                float new_sc = eval_state(cur_q4, cur_q7, cur_order, NULL);
                float delta = new_sc - cur_sc;
                if (delta > 0 || (rand_r(&seed)/(float)RAND_MAX) < expf(delta / T)) {
                    cur_sc = new_sc;
                } else {
                    // revert
                    if (type == 0) cur_q4[pos] = saved_v;
                    else if (type == 1) cur_q7[pos] = saved_v;
                    else { int tmp = cur_order[i]; cur_order[i] = cur_order[j]; cur_order[j] = tmp; }
                }
                T *= decay;
            }

            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                for (int i = 0; i < 4; i++) local_q4[i] = cur_q4[i];
                for (int i = 0; i < 7; i++) local_q7[i] = cur_q7[i];
                for (int i = 0; i < 12; i++) local_order[i] = cur_order[i];
                eval_state(cur_q4, cur_q7, cur_order, local_pt);
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                for (int i = 0; i < 4; i++) best_q4[i] = local_q4[i];
                for (int i = 0; i < 7; i++) best_q7[i] = local_q7[i];
                for (int i = 0; i < 12; i++) best_order[i] = local_order[i];
                strcpy(best_pt, local_pt);

                printf("\n>>> CANDIDATE IMPROVEMENT: Score = %.4f <<<\n", global_best_sc);
                printf("q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
                printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n",
                       best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
                printf("order: [");
                for (int i = 0; i < 12; i++) printf("%d%s", best_order[i], i==11?"]\n":", ");
                for (int r = 0; r < 12; r++) {
                    printf("  Row %2d: %.12s\n", r, best_pt + r * 12);
                }
                fflush(stdout);
            }
        }
    }

    printf("\n=== FINAL GLOBAL BEST ===\n");
    printf("Score: %.4f\n", global_best_sc);
    for (int r = 0; r < 12; r++) {
        printf("Row %2d: %.12s\n", r, best_pt + r * 12);
    }
    return 0;
}

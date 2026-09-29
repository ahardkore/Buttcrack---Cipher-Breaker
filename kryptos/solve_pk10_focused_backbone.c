#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define W 42
#define H 12
#define TOTAL_QUADS (H * (W - 3)) // 468

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
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int cols[W][H];

void init_columns() {
    int q7[7] = {0, 9, 5, 17, 10, 2, 24};
    int q8[8] = {0, 8, 16, 15, 16, 3, 6, 20};
    int q9[9] = {16, 0, 19, 9, 7, 23, 6, 16, 18};

    int Z[N];
    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int c = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int p = (c - k + 26) % 26;
        Z[i] = KRYPTOS[p] - 'A';
    }

    for (int c = 0; c < W; c++) {
        for (int r = 0; r < H; r++) {
            cols[c][r] = Z[c * H + r];
        }
    }
}

static inline float eval_order(const int *p, int *out_defects, float *out_raw) {
    float opt_sc = 0.0f;
    float raw_sc = 0.0f;
    int defects = 0;

    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W - 3; c++) {
            int a = cols[p[c  ]][r];
            int b = cols[p[c+1]][r];
            int c_char = cols[p[c+2]][r];
            int d = cols[p[c+3]][r];

            float sc = quad[a][b][c_char][d];
            raw_sc += sc;
            opt_sc += sc;
            if (!valid_quad[a][b][c_char][d]) {
                defects++;
                opt_sc -= 15.0f;
            }
        }
    }

    if (out_defects) *out_defects = defects;
    if (out_raw) *out_raw = raw_sc / TOTAL_QUADS;
    return opt_sc / TOTAL_QUADS;
}

int main(int argc, char **argv) {
    load_quads();
    init_columns();

    int restarts = (argc > 1) ? atoi(argv[1]) : 200;
    int steps_per_restart = (argc > 2) ? atoi(argv[2]) : 80000;

    const int init_order[W] = {
        29, 1, 34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16, 20, 37, 39,
        7, 31, 33, 32, 36, 22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6, 24, 5, 4, 40
    };

    // Identified 7 defect columns:
    // Pos 0, 1, 2: {29, 1, 34}
    // Pos 25, 26, 27, 28: {36, 22, 35, 27}
    const int loose_cols[7] = {29, 1, 34, 36, 22, 35, 27};
    int is_loose[W] = {0};
    for (int i = 0; i < 7; i++) is_loose[loose_cols[i]] = 1;

    int init_def = 0; float init_raw = 0.0f;
    float init_opt = eval_order(init_order, &init_def, &init_raw);

    printf("======================================================================\n");
    printf("PK10 Focused Backbone & Defect-Column Placement Engine\n");
    printf("Initial: RawScore=%.4f | Defects=%d / %d (%.1f%% valid)\n",
           init_raw, init_def, TOTAL_QUADS, (1.0f - (float)init_def/TOTAL_QUADS)*100.0f);
    printf("Loose defect columns: {29, 1, 34, 36, 22, 35, 27}\n");
    printf("Restarts: %d | Steps per restart: %d\n", restarts, steps_per_restart);
    printf("======================================================================\n\n");

    float global_best_opt = init_opt;
    float global_best_raw = init_raw;
    int global_min_def = init_def;
    int global_order[W];
    memcpy(global_order, init_order, sizeof(init_order));

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 443322 + omp_get_thread_num() * 12345;

        #pragma omp for schedule(dynamic, 1)
        for (int rep = 0; rep < restarts; rep++) {
            int order[W];
            memcpy(order, init_order, sizeof(order));

            if (rep > 0) {
                // Randomly relocate the 7 loose columns
                for (int k = 0; k < 7; k++) {
                    int c_val = loose_cols[k];
                    // find position of c_val
                    int cur_pos = -1;
                    for (int i = 0; i < W; i++) if (order[i] == c_val) { cur_pos = i; break; }
                    // pick new position
                    int new_pos = rand_r(&seed) % W;
                    if (cur_pos != new_pos) {
                        int val = order[cur_pos];
                        if (cur_pos < new_pos) for (int i = cur_pos; i < new_pos; i++) order[i] = order[i+1];
                        else for (int i = cur_pos; i > new_pos; i--) order[i] = order[i-1];
                        order[new_pos] = val;
                    }
                }
            }

            int cur_def = 0; float cur_raw = 0.0f;
            float cur_opt = eval_order(order, &cur_def, &cur_raw);

            float temp = 0.25f;
            float cooling = powf(0.0005f / temp, 1.0f / steps_per_restart);

            for (int s = 0; s < steps_per_restart; s++) {
                int backup[W];
                memcpy(backup, order, sizeof(order));

                int move_type = rand_r(&seed) % 100;
                if (move_type < 60) {
                    // Pick one of the 7 loose columns and move it to a random position
                    int loose_idx = rand_r(&seed) % 7;
                    int c_val = loose_cols[loose_idx];
                    int cur_pos = -1;
                    for (int i = 0; i < W; i++) if (order[i] == c_val) { cur_pos = i; break; }
                    int new_pos = rand_r(&seed) % W;
                    if (cur_pos != new_pos) {
                        int val = order[cur_pos];
                        if (cur_pos < new_pos) for (int i = cur_pos; i < new_pos; i++) order[i] = order[i+1];
                        else for (int i = cur_pos; i > new_pos; i--) order[i] = order[i-1];
                        order[new_pos] = val;
                    }
                } else if (move_type < 85) {
                    // Swap two loose columns
                    int l1 = rand_r(&seed) % 7;
                    int l2 = rand_r(&seed) % 7;
                    if (l1 != l2) {
                        int p1 = -1, p2 = -1;
                        for (int i = 0; i < W; i++) {
                            if (order[i] == loose_cols[l1]) p1 = i;
                            if (order[i] == loose_cols[l2]) p2 = i;
                        }
                        int t = order[p1]; order[p1] = order[p2]; order[p2] = t;
                    }
                } else {
                    // General small swap
                    int a = rand_r(&seed) % W;
                    int b = rand_r(&seed) % W;
                    int t = order[a]; order[a] = order[b]; order[b] = t;
                }

                int new_def = 0; float new_raw = 0.0f;
                float new_opt = eval_order(order, &new_def, &new_raw);

                float delta = new_opt - cur_opt;
                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_opt = new_opt;
                    cur_raw = new_raw;
                    cur_def = new_def;
                } else {
                    memcpy(order, backup, sizeof(order));
                }

                temp *= cooling;
            }

            #pragma omp critical
            {
                if (cur_def < global_min_def || (cur_def == global_min_def && cur_raw > global_best_raw)) {
                    global_best_opt = cur_opt;
                    global_best_raw = cur_raw;
                    global_min_def = cur_def;
                    memcpy(global_order, order, sizeof(order));

                    printf("[Thread %d | Rep %d] Record: RawScore=%.4f | Defects=%d / %d (%.1f%% valid)\n",
                           omp_get_thread_num(), rep, global_best_raw, global_min_def, TOTAL_QUADS,
                           (1.0f - (float)global_min_def / TOTAL_QUADS) * 100.0f);
                    fflush(stdout);

                    FILE *fout = fopen("pk10_focused_best.txt", "w");
                    if (fout) {
                        fprintf(fout, "# Record RawScore=%.4f | Defects=%d / %d\n", global_best_raw, global_min_def, TOTAL_QUADS);
                        fprintf(fout, "Order: [");
                        for (int k = 0; k < W; k++) fprintf(fout, "%d%s", order[k], k < W-1 ? ", " : "]\n\n");
                        for (int r = 0; r < H; r++) {
                            fprintf(fout, "Row %2d: ", r);
                            for (int c = 0; c < W; c++) fputc('A' + cols[order[c]][r], fout);
                            fputc('\n', fout);
                        }
                        fclose(fout);
                    }
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("\n======================================================================\n");
    printf("FOCUSED ENGINE COMPLETED in %.2f s\n", t1 - t0);
    printf("Final Best: RawScore=%.4f | Min Defects=%d / %d (%.1f%% valid)\n",
           global_best_raw, global_min_def, TOTAL_QUADS, (1.0f - (float)global_min_def/TOTAL_QUADS)*100.0f);
    printf("======================================================================\n");

    return 0;
}

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

// Compute score of the entire 42-column order:
static inline float eval_order(const int *p, int *out_defects, float *out_raw) {
    float total_opt = 0.0f;
    float total_raw = 0.0f;
    int defects = 0;

    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W - 3; c++) {
            int a = cols[p[c  ]][r];
            int b = cols[p[c+1]][r];
            int c_char = cols[p[c+2]][r];
            int d = cols[p[c+3]][r];

            float sc = quad[a][b][c_char][d];
            total_raw += sc;
            total_opt += sc;
            if (!valid_quad[a][b][c_char][d]) {
                defects++;
                total_opt -= 15.0f;
            }
        }
    }

    if (out_defects) *out_defects = defects;
    if (out_raw) *out_raw = total_raw / TOTAL_QUADS;
    return total_opt / TOTAL_QUADS;
}

// Compute score contribution only around a window [w_start, w_end]:
static inline float eval_window_subscore(const int *p, int w_start, int w_end, int *out_defects) {
    int q_start = w_start - 3; if (q_start < 0) q_start = 0;
    int q_end = w_end; if (q_end > W - 3) q_end = W - 3;

    float opt_sc = 0.0f;
    int def = 0;
    for (int r = 0; r < H; r++) {
        for (int c = q_start; c < q_end; c++) {
            int a = cols[p[c  ]][r];
            int b = cols[p[c+1]][r];
            int c_char = cols[p[c+2]][r];
            int d = cols[p[c+3]][r];

            float sc = quad[a][b][c_char][d];
            opt_sc += sc;
            if (!valid_quad[a][b][c_char][d]) {
                def++;
                opt_sc -= 15.0f;
            }
        }
    }
    if (out_defects) *out_defects = def;
    return opt_sc;
}

int main(int argc, char **argv) {
    load_quads();
    init_columns();

    int base_order[W] = {
        29, 1, 34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16, 20, 37, 39,
        7, 31, 33, 32, 36, 22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6, 24, 5, 4, 40
    };

    int cur_def = 0; float cur_raw = 0.0f;
    float cur_opt = eval_order(base_order, &cur_def, &cur_raw);

    printf("======================================================================\n");
    printf("PK10 Sliding-Window Defect Annealer\n");
    printf("Initial: RawScore=%.4f | Defects=%d / %d (%.1f%% valid)\n",
           cur_raw, cur_def, TOTAL_QUADS, (1.0f - (float)cur_def/TOTAL_QUADS)*100.0f);
    printf("======================================================================\n\n");

    int sweeps = (argc > 1) ? atoi(argv[1]) : 15;
    unsigned int seed = 123456;

    int order[W];
    memcpy(order, base_order, sizeof(order));

    for (int sweep = 0; sweep < sweeps; sweep++) {
        int win_sizes[] = {10, 12, 8, 14};
        int num_sizes = sizeof(win_sizes)/sizeof(win_sizes[0]);
        int win_size = win_sizes[sweep % num_sizes];

        printf("--- Sweep %2d / %2d (Window Size: %d) ---\n", sweep + 1, sweeps, win_size);

        // Slide window from left to right with step 3
        for (int w_start = 0; w_start <= W - win_size; w_start += 3) {
            int w_end = w_start + win_size;

            float cur_sub = eval_window_subscore(order, w_start, w_end, NULL);
            float temp = 0.20f;
            int steps = 15000;
            float cooling = powf(0.001f / temp, 1.0f / steps);

            for (int s = 0; s < steps; s++) {
                int a = w_start + (rand_r(&seed) % win_size);
                int b = w_start + (rand_r(&seed) % win_size);
                if (a == b) continue;

                int backup[W];
                memcpy(backup, order, sizeof(order));

                int move_type = rand_r(&seed) % 100;
                if (move_type < 50) {
                    // 2-opt within window
                    if (a > b) { int t = a; a = b; b = t; }
                    while (a < b) { int t = order[a]; order[a] = order[b]; order[b] = t; a++; b--; }
                } else if (move_type < 80) {
                    // Swap within window
                    int t = order[a]; order[a] = order[b]; order[b] = t;
                } else {
                    // Insertion within window
                    int val = order[a];
                    if (a < b) for (int k = a; k < b; k++) order[k] = order[k+1];
                    else for (int k = a; k > b; k--) order[k] = order[k-1];
                    order[b] = val;
                }

                float new_sub = eval_window_subscore(order, w_start, w_end, NULL);
                float delta = new_sub - cur_sub;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sub = new_sub;
                } else {
                    memcpy(order, backup, sizeof(order));
                }
                temp *= cooling;
            }
        }

        // Evaluate overall state after this sweep
        int d = 0; float raw = 0.0f;
        float opt = eval_order(order, &d, &raw);

        printf("  After Sweep %2d: RawScore=%.4f | Defects=%d / %d (%.1f%% valid)\n",
               sweep + 1, raw, d, TOTAL_QUADS, (1.0f - (float)d/TOTAL_QUADS)*100.0f);

        if (d < cur_def || (d == cur_def && raw > cur_raw)) {
            cur_def = d;
            cur_raw = raw;
            cur_opt = opt;
            printf("  *** NEW RECORD: RawScore=%.4f | Defects=%d ***\n", cur_raw, cur_def);

            FILE *fout = fopen("pk10_sliding_best.txt", "w");
            if (fout) {
                fprintf(fout, "# Record RawScore=%.4f | Defects=%d / %d\n", cur_raw, cur_def, TOTAL_QUADS);
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

    printf("\n======================================================================\n");
    printf("SLIDING-WINDOW ANNEALING FINISHED: Best RawScore=%.4f | Min Defects=%d\n", cur_raw, cur_def);
    printf("======================================================================\n");

    return 0;
}

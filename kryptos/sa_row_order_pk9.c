#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define W 12
#define H 12
#define N 144

static float quadgrams[26][26][26][26];

static const char *rows[12] = {
    "IHAGSIRROWIN",
    "ODCKIRMHOLOH",
    "UGONSPROMEOF",
    "DENITUTORNUN",
    "ONIAMHANDFIS",
    "SIRANDYWITFO",
    "CCHOAFEAGHDO",
    "TYIFOTDENDNC",
    "BTERITFYENAS",
    "ADESIRLDDIFI",
    "ISGREATILOFS",
    "HODESHAMSPOF"
};

void load_quads() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    quadgrams[i][j][k][l] = floor_val;

    FILE *f = fopen("english_quadgrams.txt", "r");
    char line[64];
    double total = 5348433.0;
    while (fgets(line, sizeof(line), f)) {
        char g[5]; double cnt;
        if (sscanf(line, "%4s %lf", g, &cnt) == 2) {
            int a = g[0]-'A', b = g[1]-'A', c = g[2]-'A', d = g[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quadgrams[a][b][c][d] = (float)log10(cnt / total);
            }
        }
    }
    fclose(f);
}

static inline float eval_full_pt(const int *row_order, int *pt_out) {
    int idx = 0;
    for (int r = 0; r < H; r++) {
        int r_idx = row_order[r];
        for (int c = 0; c < W; c++) {
            pt_out[idx++] = rows[r_idx][c] - 'A';
        }
    }
    float sc = 0;
    for (int i = 0; i < N - 3; i++) {
        sc += quadgrams[pt_out[i]][pt_out[i+1]][pt_out[i+2]][pt_out[i+3]];
    }
    return sc / (N - 3);
}

static inline unsigned int xorshift32(unsigned int *state) {
    unsigned int x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

int main() {
    load_quads();

    printf("Starting Row Order SA across 10,000 restarts...\n");

    float global_best_sc = -1e9f;
    int global_best_order[H];
    char global_best_pt[N+1];

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 1234567));

        #pragma omp for
        for (int run = 0; run < 10000; run++) {
            int order[H];
            for (int i=0; i<H; i++) order[i] = i;
            for (int i=H-1; i>0; i--) {
                int j = xorshift32(&seed) % (i+1);
                int tmp = order[i]; order[i] = order[j]; order[j] = tmp;
            }

            int pt[N];
            float cur_sc = eval_full_pt(order, pt);
            float run_best_sc = cur_sc;
            int run_best_order[H];
            memcpy(run_best_order, order, sizeof(order));

            float temp = 0.5f;
            float cooling = 0.999f;
            for (int step = 0; step < 5000; step++) {
                int i = xorshift32(&seed) % H;
                int j = xorshift32(&seed) % H;
                while (i == j) j = xorshift32(&seed) % H;

                int tmp = order[i]; order[i] = order[j]; order[j] = tmp;
                float new_sc = eval_full_pt(order, pt);
                float delta = new_sc - cur_sc;

                if (delta > 0 || ((float)xorshift32(&seed) / 4294967296.0f) < expf(delta / temp)) {
                    cur_sc = new_sc;
                    if (cur_sc > run_best_sc) {
                        run_best_sc = cur_sc;
                        memcpy(run_best_order, order, sizeof(order));
                    }
                } else {
                    tmp = order[i]; order[i] = order[j]; order[j] = tmp;
                }
                temp *= cooling;
            }

            #pragma omp critical
            {
                if (run_best_sc > global_best_sc) {
                    global_best_sc = run_best_sc;
                    memcpy(global_best_order, run_best_order, sizeof(order));
                    int best_pt_arr[N];
                    eval_full_pt(global_best_order, best_pt_arr);
                    for (int i=0; i<N; i++) global_best_pt[i] = best_pt_arr[i] + 'A';
                    global_best_pt[N] = 0;
                    printf("[Run %4d] New Best: %.4f | Order: ", run, run_best_sc);
                    for (int i=0; i<H; i++) printf("%d ", global_best_order[i]);
                    printf("\n  PT: %s\n", global_best_pt);
                }
            }
        }
    }

    printf("\nGLOBAL BEST FULL PLAINTEXT (Score: %.4f):\n%s\n", global_best_sc, global_best_pt);
    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 144
#define W 12
#define NUM_ORBITS 36

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static const int q7[7] = {0, 2, 9, 23, 23, 6, 20};

typedef struct {
    int r, c;
} Point;

static Point orbits[NUM_ORBITS][4];
static float quadgrams[26][26][26][26];

Point rot90_cw(Point p, int n) {
    Point out = { p.c, n - 1 - p.r };
    return out;
}

void build_orbits() {
    int seen[W][W] = {0};
    int count = 0;
    for (int r = 0; r < W; r++) {
        for (int c = 0; c < W; c++) {
            if (seen[r][c]) continue;
            Point p = {r, c};
            for (int rot = 0; rot < 4; rot++) {
                orbits[count][rot] = p;
                seen[p.r][p.c] = 1;
                p = rot90_cw(p, W);
            }
            count++;
        }
    }
}

void load_quads() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    quadgrams[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
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

// Fast inline insertion sort for 36 points
static inline void sort_36_points(Point *arr) {
    for (int i = 1; i < NUM_ORBITS; i++) {
        Point key = arr[i];
        int key_val = key.r * W + key.c;
        int j = i - 1;
        while (j >= 0 && (arr[j].r * W + arr[j].c) > key_val) {
            arr[j + 1] = arr[j];
            j--;
        }
        arr[j + 1] = key;
    }
}

// Decode Fleissner grille
static inline void decode_fleissner(const int *cipher_letters, const int *choice, int *plain) {
    int grid[W][W];
    for (int r = 0; r < W; r++) {
        for (int c = 0; c < W; c++) {
            grid[r][c] = cipher_letters[r * W + c];
        }
    }

    Point current[NUM_ORBITS];
    for (int i = 0; i < NUM_ORBITS; i++) {
        current[i] = orbits[i][choice[i]];
    }

    int out_idx = 0;
    for (int turn = 0; turn < 4; turn++) {
        Point sorted_holes[NUM_ORBITS];
        memcpy(sorted_holes, current, sizeof(current));
        sort_36_points(sorted_holes);

        for (int i = 0; i < NUM_ORBITS; i++) {
            plain[out_idx++] = grid[sorted_holes[i].r][sorted_holes[i].c];
        }

        for (int i = 0; i < NUM_ORBITS; i++) {
            current[i] = rot90_cw(current[i], W);
        }
    }
}

static inline unsigned int xorshift32(unsigned int *state) {
    unsigned int x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

int main(int argc, char **argv) {
    load_quads();
    build_orbits();

    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int ct_k[N];
    for (int i=0; i<N; i++) ct_k[i] = k2i[(int)CT[i]];

    int restarts = (argc > 1) ? atoi(argv[1]) : 128;
    int steps = (argc > 2) ? atoi(argv[2]) : 500000;

    printf("Starting Ultra-Fast Fleissner Grille Simulated Annealing: %d restarts, %d steps each\n",
           restarts, steps);

    float global_best_sc = -1e9f;
    char global_best_pt[N+1];
    int global_best_choice[NUM_ORBITS];
    int global_best_parity = 0;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 1234567));

        #pragma omp for schedule(dynamic, 1)
        for (int run = 0; run < restarts; run++) {
            // Focus on Parity 7, 0, 1, 2, 3
            int parity_list[8] = {7, 0, 1, 2, 3, 4, 5, 6};
            int parity = parity_list[run % 8];
            int q4_bits[4];
            for (int b=0; b<4; b++) q4_bits[b] = ((parity >> b) & 1) * 13;

            int Z_std[N];
            for (int i=0; i<N; i++) {
                int shift = (q7[i % 7] + q4_bits[i % 4]) % 26;
                int z_kr = (ct_k[i] - shift + 26) % 26;
                Z_std[i] = ALPH[z_kr] - 'A';
            }

            int choice[NUM_ORBITS];
            for (int i=0; i<NUM_ORBITS; i++) choice[i] = xorshift32(&seed) % 4;

            int plain[N];
            decode_fleissner(Z_std, choice, plain);

            float cur_sc = 0;
            for (int i=0; i<N-3; i++) {
                cur_sc += quadgrams[plain[i]][plain[i+1]][plain[i+2]][plain[i+3]];
            }
            cur_sc /= (N - 3);

            float best_sc = cur_sc;
            int best_choice[NUM_ORBITS];
            memcpy(best_choice, choice, sizeof(choice));

            float temp = 1.2f;
            float cooling = expf(logf(0.002f / 1.2f) / steps);

            for (int step = 0; step < steps; step++) {
                int orb = xorshift32(&seed) % NUM_ORBITS;
                int old_val = choice[orb];
                int new_val = (old_val + 1 + (xorshift32(&seed) % 3)) % 4;
                choice[orb] = new_val;

                decode_fleissner(Z_std, choice, plain);
                float new_sc = 0;
                for (int i=0; i<N-3; i++) {
                    new_sc += quadgrams[plain[i]][plain[i+1]][plain[i+2]][plain[i+3]];
                }
                new_sc /= (N - 3);

                float delta = new_sc - cur_sc;
                if (delta > 0 || ((float)xorshift32(&seed) / 4294967296.0f) < expf(delta / temp)) {
                    cur_sc = new_sc;
                    if (cur_sc > best_sc) {
                        best_sc = cur_sc;
                        memcpy(best_choice, choice, sizeof(choice));
                    }
                } else {
                    choice[orb] = old_val;
                }

                temp *= cooling;
            }

            #pragma omp critical
            {
                if (best_sc > global_best_sc) {
                    global_best_sc = best_sc;
                    global_best_parity = parity;
                    memcpy(global_best_choice, best_choice, sizeof(best_choice));
                    decode_fleissner(Z_std, best_choice, plain);
                    for (int i=0; i<N; i++) global_best_pt[i] = plain[i] + 'A';
                    global_best_pt[N] = 0;

                    printf("[Run %2d] New Best: %.4f (Parity %d)\n  PT: %s\n",
                           run, best_sc, parity, global_best_pt);
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f seconds! Global best: %.4f (Parity %d)\nPT: %s\n",
           elapsed, global_best_sc, global_best_parity, global_best_pt);

    return 0;
}

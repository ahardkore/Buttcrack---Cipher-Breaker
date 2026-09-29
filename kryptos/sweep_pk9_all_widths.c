#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const int q4[4] = {16, 23, 22, 18};
static const int q7[7] = {10, 19, 17, 25, 16, 18, 10};

static int alpha_to_std[26];
static char X[N + 1];
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
    for (int i = 0; i < N; i++) {
        int c_idx = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
        int k = (q4[i % 4] + q7[i % 7]) % 26;
        int p = (c_idx - k + 26) % 26;
        X[i] = 'A' + alpha_to_std[p];
    }
    X[N] = '\0';
}

static inline float score_text(const char *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]-'A'][pt[i+1]-'A'][pt[i+2]-'A'][pt[i+3]-'A'];
    }
    return s / (N - 3);
}

// Test width W (H = 144 / W)
void test_width(int W) {
    int H = N / W;
    printf("\n=== Testing Width %d (Height %d) ===\n", W, H);

    // Columns are C_k = X[k*H ... (k+1)*H - 1]
    char cols[32][64];
    for (int k = 0; k < W; k++) {
        for (int r = 0; r < H; r++) {
            cols[k][r] = X[k * H + r];
        }
    }

    if (W <= 10) {
        // Exhaustive permutation
        int perm[16];
        for (int i = 0; i < W; i++) perm[i] = i;
        
        long long total = 1;
        for (int i = 1; i <= W; i++) total *= i;

        float best_s = -999.0f;
        int best_perm[16];
        char best_pt[N + 1];

        // Generate permutations
        void permute(int depth, int used, int *cur_p) {
            if (depth == W) {
                char pt[N + 1];
                int idx = 0;
                for (int r = 0; r < H; r++) {
                    for (int c = 0; c < W; c++) {
                        pt[idx++] = cols[cur_p[c]][r];
                    }
                }
                pt[N] = '\0';
                float sc = score_text(pt);
                if (sc > best_s) {
                    best_s = sc;
                    for (int i = 0; i < W; i++) best_perm[i] = cur_p[i];
                    strcpy(best_pt, pt);
                }
                return;
            }
            for (int i = 0; i < W; i++) {
                if (!(used & (1 << i))) {
                    cur_p[depth] = i;
                    permute(depth + 1, used | (1 << i), cur_p);
                }
            }
        }

        int cur_p[16];
        permute(0, 0, cur_p);

        printf("Width %d Exhaustive Complete! Best Score = %.4f\n", W, best_s);
        printf("Order: [");
        for (int i = 0; i < W; i++) printf("%d%s", best_perm[i], i==W-1?"]\n":", ");
        printf("Plaintext: %.120s...\n", best_pt);
    } else {
        // Simulated annealing / beam search for W > 10
        printf("Width %d: running deep simulated annealing (5000 restarts)...\n", W);
        float best_s = -999.0f;
        int best_perm[32];
        char best_pt[N + 1];

        #pragma omp parallel
        {
            unsigned int seed = 42 + omp_get_thread_num() * 7777;
            float local_best_s = -999.0f;
            int local_best_perm[32];
            char local_best_pt[N + 1];

            #pragma omp for
            for (int r = 0; r < 5000; r++) {
                int p[32];
                for (int i = 0; i < W; i++) p[i] = i;
                // Fisher-Yates shuffle
                for (int i = W - 1; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                }

                char pt[N + 1];
                int idx = 0;
                for (int row = 0; row < H; row++) {
                    for (int col = 0; col < W; col++) {
                        pt[idx++] = cols[p[col]][row];
                    }
                }
                pt[N] = '\0';
                float cur_sc = score_text(pt);

                float T = 5.0f;
                float T_end = 0.05f;
                int steps = 5000;
                float decay = powf(T_end / T, 1.0f / steps);

                for (int step = 0; step < steps; step++) {
                    int i = rand_r(&seed) % W;
                    int j = rand_r(&seed) % W;
                    if (i == j) continue;

                    int tmp = p[i]; p[i] = p[j]; p[j] = tmp;

                    idx = 0;
                    for (int row = 0; row < H; row++) {
                        for (int col = 0; col < W; col++) {
                            pt[idx++] = cols[p[col]][row];
                        }
                    }
                    pt[N] = '\0';
                    float new_sc = score_text(pt);

                    float delta = new_sc - cur_sc;
                    if (delta > 0 || (rand_r(&seed)/(float)RAND_MAX) < expf(delta / T)) {
                        cur_sc = new_sc;
                    } else {
                        // revert
                        tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                    }
                    T *= decay;
                }

                if (cur_sc > local_best_s) {
                    local_best_s = cur_sc;
                    for (int i = 0; i < W; i++) local_best_perm[i] = p[i];
                    idx = 0;
                    for (int row = 0; row < H; row++) {
                        for (int col = 0; col < W; col++) {
                            local_best_pt[idx++] = cols[p[col]][row];
                        }
                    }
                    local_best_pt[N] = '\0';
                }
            }

            #pragma omp critical
            {
                if (local_best_s > best_s) {
                    best_s = local_best_s;
                    for (int i = 0; i < W; i++) best_perm[i] = local_best_perm[i];
                    strcpy(best_pt, local_best_pt);
                }
            }
        }

        printf("Width %d SA Complete! Best Score = %.4f\n", W, best_s);
        printf("Order: [");
        for (int i = 0; i < W; i++) printf("%d%s", best_perm[i], i==W-1?"]\n":", ");
        printf("Plaintext: %.120s...\n", best_pt);
    }
}

int main() {
    init_tables();
    load_quadgrams();

    printf("Sweeping all possible single columnar transposition widths on X (len 144)...\n");

    test_width(6);
    test_width(8);
    test_width(9);
    test_width(12);
    test_width(16);
    test_width(18);

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 504

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int C[N];

// Fast slice IoC mod 13
static inline float slice_ioc_mod13(const int *stream, int p) {
    int total_num = 0;
    int total_den = 0;
    for (int rem = 0; rem < p; rem++) {
        int counts[13] = {0};
        int n_sub = 0;
        for (int i = rem; i < N; i += p) {
            counts[stream[i]]++;
            n_sub++;
        }
        if (n_sub > 1) {
            int num = 0;
            for (int k = 0; k < 13; k++) num += counts[k] * (counts[k] - 1);
            total_num += num;
            total_den += n_sub * (n_sub - 1);
        }
    }
    return (total_den > 0) ? (float)total_num / (float)total_den : 0.0f;
}

static inline float eval_triple_ioc(const int *stream) {
    return slice_ioc_mod13(stream, 7) + slice_ioc_mod13(stream, 8) + slice_ioc_mod13(stream, 9);
}

// Single columnar decode
void single_col_decode(const int *in, int W, int H, const int *order, int *out) {
    int cols[W][H];
    int idx = 0;
    for (int c = 0; c < W; c++) {
        int phys = order[c];
        for (int r = 0; r < H; r++) {
            cols[phys][r] = in[idx++];
        }
    }
    int out_idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            out[out_idx++] = cols[c][r];
        }
    }
}

// Double columnar decode: undo order2 (W2, H2), then undo order1 (W1, H1)
void double_col_decode(const int *in, int W1, int H1, const int *order1,
                       int W2, int H2, const int *order2, int *out) {
    int inter[N];
    single_col_decode(in, W2, H2, order2, inter);
    single_col_decode(inter, W1, H1, order1, out);
}

void test_pair(int W1, int W2, int num_restarts, int steps_per_restart) {
    int H1 = N / W1;
    int H2 = N / W2;

    printf("=== Testing Double Columnar (%d x %d) -> (%d x %d) on PK10 ===\n", W1, H1, W2, H2);

    float global_best_score = -1.0f;
    int best_order1[64], best_order2[64];

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 10007 + W1 * 101 + W2 * 31;
        int local_best_order1[64], local_best_order2[64];
        float local_best_score = -1.0f;

        #pragma omp for schedule(dynamic, 1)
        for (int restart = 0; restart < num_restarts; restart++) {
            int cur_order1[64], cur_order2[64];
            for (int i = 0; i < W1; i++) cur_order1[i] = i;
            for (int i = 0; i < W2; i++) cur_order2[i] = i;

            // Shuffle initial orders
            for (int i = W1 - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = cur_order1[i]; cur_order1[i] = cur_order1[j]; cur_order1[j] = tmp;
            }
            for (int i = W2 - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = cur_order2[i]; cur_order2[i] = cur_order2[j]; cur_order2[j] = tmp;
            }

            int stream[N];
            double_col_decode(C, W1, H1, cur_order1, W2, H2, cur_order2, stream);
            float cur_sc = eval_triple_ioc(stream);

            float T = 0.05f;
            float cooling = 0.9995f;

            for (int step = 0; step < steps_per_restart; step++) {
                T *= cooling;
                int which = rand_r(&seed) % 2;

                int i1, i2;
                if (which == 0) {
                    i1 = rand_r(&seed) % W1;
                    i2 = rand_r(&seed) % W1;
                    if (i1 == i2) continue;
                    int tmp = cur_order1[i1]; cur_order1[i1] = cur_order1[i2]; cur_order1[i2] = tmp;
                } else {
                    i1 = rand_r(&seed) % W2;
                    i2 = rand_r(&seed) % W2;
                    if (i1 == i2) continue;
                    int tmp = cur_order2[i1]; cur_order2[i1] = cur_order2[i2]; cur_order2[i2] = tmp;
                }

                double_col_decode(C, W1, H1, cur_order1, W2, H2, cur_order2, stream);
                float new_sc = eval_triple_ioc(stream);
                float delta = new_sc - cur_sc;

                if (delta > 0 || (float)rand_r(&seed) / RAND_MAX < expf(delta / T)) {
                    cur_sc = new_sc;
                    if (cur_sc > local_best_score) {
                        local_best_score = cur_sc;
                        memcpy(local_best_order1, cur_order1, W1 * sizeof(int));
                        memcpy(local_best_order2, cur_order2, W2 * sizeof(int));
                    }
                } else {
                    // Revert swap
                    if (which == 0) {
                        int tmp = cur_order1[i1]; cur_order1[i1] = cur_order1[i2]; cur_order1[i2] = tmp;
                    } else {
                        int tmp = cur_order2[i1]; cur_order2[i1] = cur_order2[i2]; cur_order2[i2] = tmp;
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_score > global_best_score) {
                global_best_score = local_best_score;
                memcpy(best_order1, local_best_order1, W1 * sizeof(int));
                memcpy(best_order2, local_best_order2, W2 * sizeof(int));
            }
        }
    }

    int final_stream[N];
    double_col_decode(C, W1, H1, best_order1, W2, H2, best_order2, final_stream);
    float ioc7 = slice_ioc_mod13(final_stream, 7);
    float ioc8 = slice_ioc_mod13(final_stream, 8);
    float ioc9 = slice_ioc_mod13(final_stream, 9);

    printf("Best Triple-IoC: %.5f (IoC7=%.4f, IoC8=%.4f, IoC9=%.4f)\n",
           global_best_score, ioc7, ioc8, ioc9);
    printf("  Order1: ");
    for (int i = 0; i < W1; i++) printf("%d ", best_order1[i]);
    printf("\n  Order2: ");
    for (int i = 0; i < W2; i++) printf("%d ", best_order2[i]);
    printf("\n\n");
}

int main() {
    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    for (int i=0; i<N; i++) C[i] = k2i[(int)PK10_CT[i]] % 13;

    // Test combinations of factor widths:
    // Divisors of 504: 6, 7, 8, 9, 12, 14, 18, 21, 24
    int pairs[][2] = {
        {7, 8}, {8, 7}, {7, 9}, {9, 7}, {8, 9}, {9, 8},
        {7, 7}, {8, 8}, {9, 9},
        {6, 7}, {7, 6}, {6, 8}, {8, 6}, {6, 9}, {9, 6},
        {12, 7}, {7, 12}, {12, 8}, {8, 12}, {12, 9}, {9, 12},
        {14, 7}, {7, 14}, {14, 8}, {8, 14}, {14, 9}, {9, 14}
    };
    int n_pairs = sizeof(pairs) / sizeof(pairs[0]);

    for (int p = 0; p < n_pairs; p++) {
        test_pair(pairs[p][0], pairs[p][1], 100, 5000);
    }

    return 0;
}

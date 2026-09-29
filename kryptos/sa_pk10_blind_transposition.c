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

static inline float slice_ioc(const int *stream, int p) {
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
    return slice_ioc(stream, 7) + slice_ioc(stream, 8) + slice_ioc(stream, 9);
}

void col_dec_fast(const int *in, int W, int H, const int *order, int *out) {
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

static inline unsigned int xorshift32(unsigned int *state) {
    unsigned int x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

void test_width(int W) {
    int H = N / W;
    printf("\n--- Testing Width %2d (Grid %2d x %2d) ---\n", W, H, W);

    float global_best_sc = -1e9f;
    int global_best_order[W];

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 1234567 + W * 999));
        float local_best = -1e9f;
        int local_order[W];

        #pragma omp for
        for (int run = 0; run < 100; run++) {
            int order[W];
            for (int i=0; i<W; i++) order[i] = i;
            for (int i=W-1; i>0; i--) {
                int j = xorshift32(&seed) % (i+1);
                int tmp = order[i]; order[i] = order[j]; order[j] = tmp;
            }

            int out[N];
            col_dec_fast(C, W, H, order, out);
            float cur_sc = eval_triple_ioc(out);
            float run_best_sc = cur_sc;
            int run_best_order[W];
            memcpy(run_best_order, order, sizeof(order));

            float temp = 0.05f;
            float cooling = 0.999f;
            for (int step = 0; step < 5000; step++) {
                int i = xorshift32(&seed) % W;
                int j = xorshift32(&seed) % W;
                while (i == j) j = xorshift32(&seed) % W;

                int tmp = order[i]; order[i] = order[j]; order[j] = tmp;
                col_dec_fast(C, W, H, order, out);
                float new_sc = eval_triple_ioc(out);
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

            if (run_best_sc > local_best) {
                local_best = run_best_sc;
                memcpy(local_order, run_best_order, sizeof(order));
            }
        }

        #pragma omp critical
        {
            if (local_best > global_best_sc) {
                global_best_sc = local_best;
                memcpy(global_best_order, local_order, sizeof(global_best_order));
            }
        }
    }

    int out[N];
    col_dec_fast(C, W, H, global_best_order, out);
    float ioc7 = slice_ioc(out, 7);
    float ioc8 = slice_ioc(out, 8);
    float ioc9 = slice_ioc(out, 9);
    printf("Best Triple-IoC for W=%2d: %.5f (IoC7=%.4f, IoC8=%.4f, IoC9=%.4f)\n",
           W, global_best_sc, ioc7, ioc8, ioc9);
    if (global_best_sc > 0.270f) {
        printf(">>> SURGE DETECTED! Width %d order: ", W);
        for (int i=0; i<W; i++) printf("%d ", global_best_order[i]);
        printf("\n");
    }
}

int main() {
    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    for (int i=0; i<N; i++) C[i] = k2i[(int)PK10_CT[i]] % 13;

    int candidate_widths[] = {7, 8, 9, 12, 14, 18, 21, 24, 28, 36, 42, 56};
    int n_widths = sizeof(candidate_widths) / sizeof(candidate_widths[0]);

    for (int w = 0; w < n_widths; w++) {
        test_width(candidate_widths[w]);
    }

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int ct_kr[N];
static int ct_std[N];

// Fast slice IoC mod 13
float slice_ioc_mod13(const int *stream, int p) {
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

void test_stream(const int *stream, const char *desc) {
    float ioc7 = slice_ioc_mod13(stream, 7);
    float ioc8 = slice_ioc_mod13(stream, 8);
    float ioc9 = slice_ioc_mod13(stream, 9);

    if (ioc7 > 0.088f || ioc8 > 0.088f || ioc9 > 0.088f) {
        #pragma omp critical
        {
            printf(">>> DETECTOR HIT! [%s] <<<\n", desc);
            printf("  IoC(p=7) = %.5f | IoC(p=8) = %.5f | IoC(p=9) = %.5f\n", ioc7, ioc8, ioc9);
        }
    }
}

// Route generator
void test_routes() {
    int shapes[][2] = {
        {7, 72}, {72, 7}, {8, 63}, {63, 8}, {9, 56}, {56, 9},
        {12, 42}, {42, 12}, {14, 36}, {36, 14}, {18, 28}, {28, 18},
        {21, 24}, {24, 21}
    };
    int n_shapes = sizeof(shapes) / sizeof(shapes[0]);

    printf("Screening route transpositions across %d grid shapes...\n", n_shapes);

    for (int s = 0; s < n_shapes; s++) {
        int R = shapes[s][0];
        int C = shapes[s][1];

        // 1. Col-major read (standard matrix transpose)
        int stream_fwd[N], stream_rev[N];
        int idx = 0;
        for (int c = 0; c < C; c++) {
            for (int r = 0; r < R; r++) {
                stream_fwd[idx] = ct_kr[r * C + c];
                stream_rev[idx] = ct_kr[(R - 1 - r) * C + c];
                idx++;
            }
        }
        char desc[64];
        snprintf(desc, sizeof(desc), "Shape (%dx%d) col-major fwd", R, C);
        test_stream(stream_fwd, desc);
        snprintf(desc, sizeof(desc), "Shape (%dx%d) col-major rev", R, C);
        test_stream(stream_rev, desc);

        // 2. Boustrophedon (serpentine rows)
        idx = 0;
        for (int r = 0; r < R; r++) {
            if (r % 2 == 0) {
                for (int c = 0; c < C; c++) stream_fwd[idx++] = ct_kr[r * C + c];
            } else {
                for (int c = C - 1; c >= 0; c--) stream_fwd[idx++] = ct_kr[r * C + c];
            }
        }
        snprintf(desc, sizeof(desc), "Shape (%dx%d) boustrophedon rows", R, C);
        test_stream(stream_fwd, desc);

        // 3. Boustrophedon (serpentine cols)
        idx = 0;
        for (int c = 0; c < C; c++) {
            if (c % 2 == 0) {
                for (int r = 0; r < R; r++) stream_fwd[idx++] = ct_kr[r * C + c];
            } else {
                for (int r = R - 1; r >= 0; r--) stream_fwd[idx++] = ct_kr[r * C + c];
            }
        }
        snprintf(desc, sizeof(desc), "Shape (%dx%d) boustrophedon cols", R, C);
        test_stream(stream_fwd, desc);
    }
}

void word_to_order(const char *word, int len, int *order) {
    int used[64] = {0};
    int pos = 0;
    for (char c = 'A'; c <= 'Z'; c++) {
        for (int i = 0; i < len; i++) {
            if (word[i] == c && !used[i]) {
                order[pos++] = i;
                used[i] = 1;
            }
        }
    }
}

void test_dictionary_transposition(const char *fn, int w) {
    FILE *f = fopen(fn, "r");
    if (!f) return;

    char (*words)[32] = malloc(60000 * sizeof(*words));
    int (*orders)[32] = malloc(60000 * sizeof(*orders));
    int n_words = 0;
    char buf[64];
    while (fgets(buf, sizeof(buf), f) && n_words < 60000) {
        if (buf[strlen(buf)-1] == '\n') buf[strlen(buf)-1] = 0;
        if (buf[strlen(buf)-1] == '\r') buf[strlen(buf)-1] = 0;
        if (strlen(buf) == w) {
            for (int i=0; i<w; i++) if (buf[i]>='a'&&buf[i]<='z') buf[i]-=32;
            strcpy(words[n_words], buf);
            word_to_order(buf, w, orders[n_words]);
            n_words++;
        }
    }
    fclose(f);

    printf("Testing Width %2d (%d words from %s)...\n", w, n_words, fn);
    int H = N / w;

    #pragma omp parallel for schedule(dynamic, 100)
    for (int wi = 0; wi < n_words; wi++) {
        int stream[N];
        // Decrypt columnar: fill columns in key order, read by rows
        int idx = 0;
        int grid[600][64]; // max H is 72, max W is 42
        for (int c = 0; c < w; c++) {
            int col = orders[wi][c];
            for (int r = 0; r < H; r++) {
                grid[r][col] = ct_kr[idx++];
            }
        }
        idx = 0;
        for (int r = 0; r < H; r++) {
            for (int c = 0; c < w; c++) {
                stream[idx++] = grid[r][c];
            }
        }

        float ioc7 = slice_ioc_mod13(stream, 7);
        float ioc8 = slice_ioc_mod13(stream, 8);
        float ioc9 = slice_ioc_mod13(stream, 9);

        if (ioc7 > 0.088f || ioc8 > 0.088f || ioc9 > 0.088f) {
            #pragma omp critical
            {
                printf(">>> HIT on Width %d! Word: %s <<<\n", w, words[wi]);
                printf("  IoC(p=7) = %.5f | IoC(p=8) = %.5f | IoC(p=9) = %.5f\n", ioc7, ioc8, ioc9);
            }
        }
    }

    free(words);
    free(orders);
}

int main() {
    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    for (int i=0; i<N; i++) {
        ct_kr[i] = k2i[(int)PK10_CT[i]] % 13;
        ct_std[i] = (PK10_CT[i] - 'A') % 13;
    }

    test_routes();

    test_dictionary_transposition("words_7.txt", 7);
    test_dictionary_transposition("words_8.txt", 8);
    test_dictionary_transposition("words_9.txt", 9);
    test_dictionary_transposition("words_12.txt", 12);
    test_dictionary_transposition("words_14.txt", 14);

    printf("All blind transposition detector sweeps completed on PK10!\n");
    return 0;
}

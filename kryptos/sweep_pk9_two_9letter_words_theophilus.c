#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W1 18
#define H1 8
#define W2 8
#define H2 18

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

const char *Z_STR = "EVIJSAOMWYTEESREOXDVFTIDNMZTOXAEELTGEWSUDEMOTNBSRHEITTFDLERTTOMASEJNAEWAARSENXHEPEEDTEYOLNAEEEHSESEVITEEECFRSDEELEOPPDSEIDINYSEDSAATOEOREWOEKSEN";

static int z_arr[N];

void init_z() {
    for (int i = 0; i < N; i++) z_arr[i] = Z_STR[i] - 'A';
}

static inline void invert_col(const int *src, int w, int h, const int *perm, int *dst) {
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < h; r++) dst[r * w + col] = src[idx++];
    }
}

static inline float eval_quad(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

static inline void get_columnar_perm(const char *word, int len, int *perm) {
    for (int i = 0; i < len; i++) perm[i] = i;
    for (int i = 0; i < len - 1; i++) {
        for (int j = i + 1; j < len; j++) {
            if (word[perm[j]] < word[perm[i]] || (word[perm[j]] == word[perm[i]] && perm[j] < perm[i])) {
                int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
            }
        }
    }
}

int main() {
    load_quads();
    init_z();

    // 1. Load 9-letter words
    FILE *f9 = fopen("theophilus_w9.txt", "r");
    if (!f9) { printf("Cannot open theophilus_w9.txt\n"); exit(1); }
    char words9[500][16];
    int n9 = 0;
    char line[128];
    while (fgets(line, sizeof(line), f9)) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == 9) {
            strcpy(words9[n9++], w);
        }
    }
    fclose(f9);
    printf("Loaded %d 9-letter Theophilus words.\n", n9);

    // 2. Load 8-letter words
    FILE *f8 = fopen("theophilus_w8.txt", "r");
    if (!f8) { printf("Cannot open theophilus_w8.txt\n"); exit(1); }
    char words8[500][16];
    int perms8[500][W2];
    int n8 = 0;
    while (fgets(line, sizeof(line), f8)) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == W2) {
            get_columnar_perm(w, W2, perms8[n8]);
            strcpy(words8[n8], w);
            n8++;
        }
    }
    fclose(f8);
    printf("Loaded %d 8-letter Theophilus words.\n", n8);

    long long total_triples = (long long)n9 * n9 * n8;
    printf("======================================================================\n");
    printf("Exhaustively Sweeping %lld Triples: (Word9A + Word9B, Word8)\n", total_triples * 2);
    printf("======================================================================\n");

    float global_best_sc = -999.0f;
    char best_w9a[16] = "", best_w9b[16] = "", best_w8[16] = "";
    int best_mode = -1;
    char best_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float loc_best_sc = -999.0f;
        char loc_w9a[16] = "", loc_w9b[16] = "", loc_w8[16] = "";
        int loc_mode = -1;
        char loc_pt[N + 1];

        #pragma omp for schedule(dynamic, 1)
        for (int i = 0; i < n9; i++) {
            char comp[20];
            int p18[W1];
            for (int j = 0; j < n9; j++) {
                sprintf(comp, "%s%s", words9[i], words9[j]);
                get_columnar_perm(comp, W1, p18);

                // Mode 0: Invert W2=8 first, then W1=18
                for (int k = 0; k < n8; k++) {
                    int mid[N], pt[N];
                    invert_col(z_arr, W2, H2, perms8[k], mid);
                    invert_col(mid, W1, H1, p18, pt);
                    float sc = eval_quad(pt);

                    if (sc > loc_best_sc) {
                        loc_best_sc = sc;
                        strcpy(loc_w9a, words9[i]);
                        strcpy(loc_w9b, words9[j]);
                        strcpy(loc_w8, words8[k]);
                        loc_mode = 0;
                        for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                        loc_pt[N] = '\0';
                    }
                }

                // Mode 1: Invert W1=18 first, then W2=8
                int mid[N];
                invert_col(z_arr, W1, H1, p18, mid);
                for (int k = 0; k < n8; k++) {
                    int pt[N];
                    invert_col(mid, W2, H2, perms8[k], pt);
                    float sc = eval_quad(pt);

                    if (sc > loc_best_sc) {
                        loc_best_sc = sc;
                        strcpy(loc_w9a, words9[i]);
                        strcpy(loc_w9b, words9[j]);
                        strcpy(loc_w8, words8[k]);
                        loc_mode = 1;
                        for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                        loc_pt[N] = '\0';
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                strcpy(best_w9a, loc_w9a);
                strcpy(best_w9b, loc_w9b);
                strcpy(best_w8, loc_w8);
                best_mode = loc_mode;
                strcpy(best_pt, loc_pt);
                printf("[Thread %d] New Best: %.4f | Mode %d | Words: (%s + %s, %s)\n",
                       omp_get_thread_num(), global_best_sc, best_mode,
                       best_w9a, best_w9b, best_w8);
                printf("  PT: %.75s...\n\n", best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Evaluated %lld triples in %.3f s (%.1f M triples/sec)!\n\n",
           total_triples * 2, elapsed, (double)(total_triples * 2) / (elapsed * 1e6));

    printf("======================================================================\n");
    printf("FINAL OPTIMAL THEOPHILUS RESULT\n");
    printf("======================================================================\n");
    printf("Score: %.4f\n", global_best_sc);
    printf("Mode: %s\n", best_mode == 0 ? "W2=8 then W1=18" : "W1=18 then W2=8");
    printf("Keywords: (%s + %s, %s)\n", best_w9a, best_w9b, best_w8);
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}

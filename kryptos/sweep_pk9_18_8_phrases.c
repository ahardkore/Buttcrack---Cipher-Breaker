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

int main() {
    load_quads();
    init_z();

    // 1. Load 8-letter words from theophilus_w8.txt
    FILE *f8 = fopen("theophilus_w8.txt", "r");
    if (!f8) { printf("Cannot open theophilus_w8.txt\n"); exit(1); }
    char words8[1000][16];
    int perms8[1000][W2];
    int n8 = 0;
    char line[128];
    while (fgets(line, sizeof(line), f8)) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == W2) {
            int p[W2];
            for (int i=0; i<W2; i++) p[i] = i;
            for (int i=0; i<W2-1; i++) {
                for (int j=i+1; j<W2; j++) {
                    if (w[p[j]] < w[p[i]] || (w[p[j]] == w[p[i]] && p[j] < p[i])) {
                        int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                    }
                }
            }
            memcpy(perms8[n8], p, W2 * sizeof(int));
            strcpy(words8[n8], w);
            n8++;
        }
    }
    fclose(f8);
    printf("Loaded %d 8-letter Theophilus words.\n", n8);

    // 2. Load 18-letter phrases from apprentice_phrases_18.txt
    FILE *f18 = fopen("apprentice_phrases_18.txt", "r");
    if (!f18) { printf("Cannot open apprentice_phrases_18.txt\n"); exit(1); }
    int cap18 = 60000;
    int (*perms18)[W1] = malloc(cap18 * sizeof(*perms18));
    char (*phrases18)[24] = malloc(cap18 * sizeof(*phrases18));
    int n18 = 0;
    while (fgets(line, sizeof(line), f18)) {
        char w[64];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == W1) {
            int p[W1];
            for (int i=0; i<W1; i++) p[i] = i;
            for (int i=0; i<W1-1; i++) {
                for (int j=i+1; j<W1; j++) {
                    if (w[p[j]] < w[p[i]] || (w[p[j]] == w[p[i]] && p[j] < p[i])) {
                        int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                    }
                }
            }
            memcpy(perms18[n18], p, W1 * sizeof(int));
            strcpy(phrases18[n18], w);
            n18++;
            if (n18 >= cap18) break;
        }
    }
    fclose(f18);
    printf("Loaded %d 18-letter craft phrases.\n", n18);

    long long total = (long long)n8 * n18;
    printf("======================================================================\n");
    printf("Sweeping %lld Pairs on Z ((18, 8) and (8, 18))\n", total * 2);
    printf("======================================================================\n");

    float global_best_sc = -999.0f;
    char best_w8[16] = "", best_p18[24] = "";
    int best_mode = -1;
    char best_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float loc_best_sc = -999.0f;
        char loc_w8[16] = "", loc_p18[24] = "";
        int loc_mode = -1;
        char loc_pt[N + 1];

        // Configuration A: W2=8, then W1=18
        #pragma omp for schedule(dynamic, 1)
        for (int i8 = 0; i8 < n8; i8++) {
            int mid[N];
            invert_col(z_arr, W2, H2, perms8[i8], mid);

            for (int i18 = 0; i18 < n18; i18++) {
                int pt[N];
                invert_col(mid, W1, H1, perms18[i18], pt);
                float sc = eval_quad(pt);

                if (sc > loc_best_sc) {
                    loc_best_sc = sc;
                    strcpy(loc_w8, words8[i8]);
                    strcpy(loc_p18, phrases18[i18]);
                    loc_mode = 0;
                    for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                    loc_pt[N] = '\0';
                }
            }
        }

        // Configuration B: W1=18, then W2=8
        #pragma omp for schedule(dynamic, 4)
        for (int i18 = 0; i18 < n18; i18++) {
            int mid[N];
            invert_col(z_arr, W1, H1, perms18[i18], mid);

            for (int i8 = 0; i8 < n8; i8++) {
                int pt[N];
                invert_col(mid, W2, H2, perms8[i8], pt);
                float sc = eval_quad(pt);

                if (sc > loc_best_sc) {
                    loc_best_sc = sc;
                    strcpy(loc_w8, words8[i8]);
                    strcpy(loc_p18, phrases18[i18]);
                    loc_mode = 1;
                    for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                    loc_pt[N] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                strcpy(best_w8, loc_w8);
                strcpy(best_p18, loc_p18);
                best_mode = loc_mode;
                strcpy(best_pt, loc_pt);
                printf("[Thread %d] New Best: %.4f | Mode %d | Words: (%s, %s)\n",
                       omp_get_thread_num(), global_best_sc, best_mode, best_w8, best_p18);
                printf("  PT: %.75s...\n\n", best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Search completed in %.3f s (%.1f M evals/sec)!\n\n",
           elapsed, (double)(total * 2) / (elapsed * 1e6));

    printf("======================================================================\n");
    printf("FINAL RESULT\n");
    printf("======================================================================\n");
    printf("Score: %.4f\n", global_best_sc);
    printf("Mode: %s\n", best_mode == 0 ? "W2=8 then W1=18" : "W1=18 then W2=8");
    printf("Keywords: (%s, %s)\n", best_w8, best_p18);
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W 12
#define H 12

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

static inline void invert_columnar(const int *src, const int *perm, int *dst) {
    int idx = 0;
    for (int c_idx = 0; c_idx < W; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < H; r++) dst[r * W + col] = src[idx++];
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

    // Load permutations from words_12.txt
    FILE *f = fopen("words_12.txt", "r");
    if (!f) { printf("Cannot open words_12.txt\n"); exit(1); }

    int cap = 25000;
    int (*perms)[W] = malloc(cap * sizeof(*perms));
    char (*words)[16] = malloc(cap * sizeof(*words));
    int n_perms = 0;

    char line[128];
    while (fgets(line, sizeof(line), f)) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == W) {
            // Get order
            int p[W];
            for (int i = 0; i < W; i++) p[i] = i;
            for (int i = 0; i < W - 1; i++) {
                for (int j = i + 1; j < W; j++) {
                    if (w[p[j]] < w[p[i]] || (w[p[j]] == w[p[i]] && p[j] < p[i])) {
                        int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                    }
                }
            }
            memcpy(perms[n_perms], p, W * sizeof(int));
            strcpy(words[n_perms], w);
            n_perms++;
            if (n_perms >= cap) break;
        }
    }
    fclose(f);
    printf("Loaded %d 12-letter keywords and permutations.\n", n_perms);

    long long total_pairs = (long long)n_perms * n_perms;
    printf("======================================================================\n");
    printf("Exhaustively Sweeping All %lld Keyword Pairs (12x12, 12x12)\n", total_pairs);
    printf("======================================================================\n");

    float global_best_sc = -999.0f;
    int best_idx1 = -1, best_idx2 = -1;
    char best_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float loc_best_sc = -999.0f;
        int loc_idx1 = -1, loc_idx2 = -1;
        char loc_pt[N + 1];

        #pragma omp for schedule(dynamic, 16)
        for (int i2 = 0; i2 < n_perms; i2++) {
            int mid[N];
            invert_columnar(z_arr, perms[i2], mid);

            for (int i1 = 0; i1 < n_perms; i1++) {
                int pt[N];
                invert_columnar(mid, perms[i1], pt);
                float sc = eval_quad(pt);

                if (sc > loc_best_sc) {
                    loc_best_sc = sc;
                    loc_idx1 = i1;
                    loc_idx2 = i2;
                    for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                    loc_pt[N] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                best_idx1 = loc_idx1;
                best_idx2 = loc_idx2;
                strcpy(best_pt, loc_pt);
                printf("[Thread %d] New Best: %.4f | Words: (%s, %s)\n",
                       omp_get_thread_num(), global_best_sc,
                       words[best_idx1], words[best_idx2]);
                printf("  PT: %.75s...\n\n", best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("418M pairs evaluated in %.3f s (%.1f M pairs/sec)!\n\n",
           elapsed, (double)total_pairs / (elapsed * 1e6));

    printf("======================================================================\n");
    printf("FINAL OPTIMAL RESULT\n");
    printf("======================================================================\n");
    printf("Score: %.4f\n", global_best_sc);
    printf("Keywords: (%s, %s)\n", words[best_idx1], words[best_idx2]);
    printf("Plaintext:\n%s\n\n", best_pt);

    printf("Plaintext in 12-char rows:\n");
    for (int r = 0; r < 12; r++) {
        char buf[13];
        memcpy(buf, best_pt + r * 12, 12);
        buf[12] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}

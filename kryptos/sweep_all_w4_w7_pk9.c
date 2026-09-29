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

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int k2std[26];
static int hpos[256];

static const int p1[W1] = {5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6};
static const int p2[W2] = {4, 0, 6, 5, 3, 2, 7, 1};

static int pt_to_z[N];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK9_RAW[i]];

    int pt_to_mid[N];
    int idx = 0;
    for (int c_idx = 0; c_idx < W1; c_idx++) {
        int col = p1[c_idx];
        for (int r = 0; r < H1; r++) {
            pt_to_mid[r * W1 + col] = idx++;
        }
    }

    int mid_to_z[N];
    idx = 0;
    for (int c_idx = 0; c_idx < W2; c_idx++) {
        int col = p2[c_idx];
        for (int r = 0; r < H2; r++) {
            mid_to_z[r * W2 + col] = idx++;
        }
    }

    for (int i = 0; i < N; i++) {
        pt_to_z[i] = mid_to_z[pt_to_mid[i]];
    }
}

static inline float eval_dual_clock(const int *q4, const int *q7, int *out_pt) {
    int pt[N];
    for (int i = 0; i < N; i++) {
        int z_idx = pt_to_z[i];
        int s = (q4[z_idx % 4] + q7[z_idx % 7]) % 26;
        int p_kr = (ct_kr[z_idx] - s + 26) % 26;
        pt[i] = k2std[p_kr];
    }

    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    load_quads();
    init_tables();

    // 1. Load words_4.txt
    FILE *f4 = fopen("words_4.txt", "r");
    if (!f4) { printf("Cannot open words_4.txt\n"); exit(1); }
    char words4[10000][8];
    int q4_arr[10000][4];
    int n4 = 0;
    char line[128];
    while (fgets(line, sizeof(line), f4)) {
        char w[16];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == 4) {
            int valid = 1;
            for (int i = 0; i < 4; i++) {
                if (w[i] >= 'a' && w[i] <= 'z') w[i] -= 32;
                if (w[i] < 'A' || w[i] > 'Z') { valid = 0; break; }
            }
            if (valid) {
                strcpy(words4[n4], w);
                for (int i = 0; i < 4; i++) q4_arr[n4][i] = hpos[(unsigned char)w[i]];
                n4++;
            }
        }
    }
    fclose(f4);
    printf("Loaded %d 4-letter words.\n", n4);

    // 2. Load words_7.txt
    FILE *f7 = fopen("words_7.txt", "r");
    if (!f7) { printf("Cannot open words_7.txt\n"); exit(1); }
    int cap7 = 45000;
    char (*words7)[12] = malloc(cap7 * sizeof(*words7));
    int (*q7_arr)[7] = malloc(cap7 * sizeof(*q7_arr));
    int n7 = 0;
    while (fgets(line, sizeof(line), f7)) {
        char w[24];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == 7) {
            int valid = 1;
            for (int i = 0; i < 7; i++) {
                if (w[i] >= 'a' && w[i] <= 'z') w[i] -= 32;
                if (w[i] < 'A' || w[i] > 'Z') { valid = 0; break; }
            }
            if (valid) {
                strcpy(words7[n7], w);
                for (int i = 0; i < 7; i++) q7_arr[n7][i] = hpos[(unsigned char)w[i]];
                n7++;
                if (n7 >= cap7) break;
            }
        }
    }
    fclose(f7);
    printf("Loaded %d 7-letter words.\n", n7);

    long long total = (long long)n4 * n7;
    printf("======================================================================\n");
    printf("Exhaustively Sweeping ALL %lld Word Pairs (W4, W7) on PK9\n", total);
    printf("======================================================================\n\n");

    float global_best_sc = -999.0f;
    char best_w4[8] = "", best_w7[12] = "";
    char best_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float loc_best_sc = -999.0f;
        char loc_w4[8] = "", loc_w7[12] = "";
        char loc_pt[N + 1];

        #pragma omp for schedule(dynamic, 8)
        for (int i4 = 0; i4 < n4; i4++) {
            for (int i7 = 0; i7 < n7; i7++) {
                float sc = eval_dual_clock(q4_arr[i4], q7_arr[i7], NULL);
                if (sc > loc_best_sc) {
                    loc_best_sc = sc;
                    strcpy(loc_w4, words4[i4]);
                    strcpy(loc_w7, words7[i7]);
                    int pt[N];
                    eval_dual_clock(q4_arr[i4], q7_arr[i7], pt);
                    for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                    loc_pt[N] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                strcpy(best_w4, loc_w4);
                strcpy(best_w7, loc_w7);
                strcpy(best_pt, loc_pt);
                printf("[Thread %d] New Best: %.4f | Words: (%s, %s)\n",
                       omp_get_thread_num(), global_best_sc, best_w4, best_w7);
                printf("  PT: %.80s...\n\n", best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("SWEEP COMPLETE in %.3f s (%.1f M pairs/sec)\n",
           elapsed, (double)total / (elapsed * 1e6));
    printf("======================================================================\n");
    printf("Final Best Score: %.4f\n", global_best_sc);
    printf("Optimal Keywords: (%s, %s)\n", best_w4, best_w7);
    printf("Full Plaintext:\n%s\n\n", best_pt);

    printf("Plaintext in 8 rows of 18 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[19];
        memcpy(buf, best_pt + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %d: %s\n", r, buf);
    }

    return 0;
}

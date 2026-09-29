#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504

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

const char *Z_PK10 = "ASGKUHCPALCOWACYCCUWPMIMRUCDEOXWQBCFBATGCSKDUASKFATGMDADYLDBSOZTFRCPNLMSHNBUZUHDDDHKNENSDMIRVTYAGDBPIUKNQSTIAHBNJTHZKPTHIXEOLUSISSTDTISLRMLUYJEKXSEJUOKUKMIMCCELHHSOLNLUWIOOADAYTHKSEVACCHASRVFTSYTYEHEPDULEEOWMNNUWUWNUSZUDENLWYZAXSVNECGOENTFOTTHOREENUETOLDYGIOIULIVPRANKTXNTOIIUBWEOFAPSOSFLOMATARDTVLSEPTMHPOFPVLIRFUECBNARRBIHHGEVUYUSSEONFVFIBOPFGGHQQOLRSEBELAURUNWAKREMEEYDUQQHPFYXYGUSQWUALNHDENFAPUIUBAYLSLVGPHYISBTPORESBCLIRFNGFGIYEJOHWSWODTTIDPFSNOQTTRYDPMXTSACDOPMNRRNGGDSHFYOWEOFKDYTVUYYKSECUIMSNETBE";

static int z_arr[N];

void init_z() {
    for (int i = 0; i < N; i++) z_arr[i] = Z_PK10[i] - 'A';
}

static inline void invert_columnar(const int *src, int W, const int *perm, int *dst) {
    int H = N / W;
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

void solve_grid(int W, int restarts) {
    int H = N / W;
    float global_best_sc = -999.0f;
    int g_perm[64];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 1234 + omp_get_thread_num() * 2333 + W * 17;
        float loc_best_sc = -999.0f;
        int l_perm[64];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 10)
        for (int rep = 0; rep < restarts; rep++) {
            int perm[64];
            for (int i = 0; i < W; i++) perm[i] = i;
            for (int i = W - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
            }

            int pt[N];
            invert_columnar(z_arr, W, perm, pt);
            float cur_sc = eval_quad(pt);

            float temp = 1.8f;
            float cooling = 0.9992f;

            for (int step = 0; step < 4000; step++) {
                int c1 = rand_r(&seed) % W;
                int c2 = rand_r(&seed) % W;
                if (c1 == c2) continue;
                int tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;

                invert_columnar(z_arr, W, perm, pt);
                float sc = eval_quad(pt);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    perm[c2] = perm[c1]; perm[c1] = tmp;
                }

                temp *= cooling;
            }

            // Polish with 2-opt swaps
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int i = 0; i < W - 1; i++) {
                    for (int j = i + 1; j < W; j++) {
                        int t = perm[i]; perm[i] = perm[j]; perm[j] = t;
                        invert_columnar(z_arr, W, perm, pt);
                        float sc = eval_quad(pt);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            improved = 1;
                        } else {
                            perm[j] = perm[i]; perm[i] = t;
                        }
                    }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_perm, perm, W * sizeof(int));
                invert_columnar(z_arr, W, perm, pt);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_perm, l_perm, W * sizeof(int));
                strcpy(g_pt, l_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Grid %2d x %2d (W=%2d, %d restarts, %.2fs): Best Score = %.4f\n",
           H, W, W, restarts, elapsed, global_best_sc);
    printf("  Order: [");
    for (int i = 0; i < W; i++) printf("%d%s", g_perm[i], i==W-1?"":", ");
    printf("]\n");
    printf("  PT: %.80s...\n\n", g_pt);
}

int main(int argc, char **argv) {
    load_quads();
    init_z();

    int restarts = (argc > 1) ? atoi(argv[1]) : 2000;

    printf("======================================================================\n");
    printf("Sweeping Harmonic Transposition Factor Grids on PK10 Decoupled Z\n");
    printf("N = 504 | Restarts per grid: %d\n", restarts);
    printf("======================================================================\n\n");

    int widths[] = {24, 21, 18, 28, 14, 36, 12, 42};
    int n_widths = sizeof(widths) / sizeof(widths[0]);

    for (int i = 0; i < n_widths; i++) {
        solve_grid(widths[i], restarts);
    }

    return 0;
}

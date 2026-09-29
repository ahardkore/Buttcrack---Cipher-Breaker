#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define W1 42
#define H1 12
#define W2 36
#define H2 14

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

const char *Z_PK10 = "CSGYUHCZHLCCUACYAHURPJIMPLHHEOVWVBOUBATEESKDKASKFATLHIADTIDFSRTTHRAANLHEJNBWZUHSLDHTLENSBWIOVYYAISGAIUXNVSKXAHBLMTHZOPTHIXECGKSIBTTHTEELPMIZYJAOKSEMUOKLAMIVACELFNSCLLLUZEDCADOYSHVIEVAAEHASSVFTSYTSANEPFNLIERYMUNNRUWIKBZUFENLNCZAYTVNEAMOINYFOSKNCRECNWEKHLDYELOIUVIVPRANTKPNTAGIZBNJOHARDOSBVAMASARDKPLSIRTMHRDFAVIIRHLJGBNORPBEWHGEQWYUSEEONFVFNTDPFIEHXQRVRBESILALSWNWCKREHMEYHNQQHRLYYYEUSVNKELNFDGNBJPUINDAYLELVGPHYNYGTPAZEDBOVIPFLLFGEAGJOJWSWRLTTNBPFSLDQBTZYDOHPBSAADAPHYRRNEIDSHLYOWEOFTSATVWKYTSAHULMTWETTJ";

static int z_arr[N];

void init_z() {
    for (int i = 0; i < N; i++) z_arr[i] = Z_PK10[i] - 'A';
}

static inline void invert_columnar(const int *src, int W, int H, const int *perm, int *dst) {
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

void test_pair(int restarts) {
    printf("======================================================================\n");
    printf("Testing Double-Columnar Coupling (W1=42, W2=36) on PK10 Decoupled Z\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    float global_best_sc = -999.0f;
    int g_p1[W1], g_p2[W2];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 123 + omp_get_thread_num() * 3779;
        float loc_best_sc = -999.0f;
        int l_p1[W1], l_p2[W2];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 5)
        for (int rep = 0; rep < restarts; rep++) {
            int p1[W1], p2[W2];
            for (int i = 0; i < W1; i++) p1[i] = i;
            for (int i = W1 - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = p1[i]; p1[i] = p1[j]; p1[j] = tmp;
            }
            for (int i = 0; i < W2; i++) p2[i] = i;
            for (int i = W2 - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = p2[i]; p2[i] = p2[j]; p2[j] = tmp;
            }

            int mid[N], pt[N];
            invert_columnar(z_arr, W2, H2, p2, mid);
            invert_columnar(mid, W1, H1, p1, pt);
            float cur_sc = eval_quad(pt);

            float temp = 1.8f;
            float cooling = 0.9991f;

            for (int step = 0; step < 4000; step++) {
                int layer = rand_r(&seed) % 2;
                int c1, c2, tmp;

                if (layer == 0) {
                    c1 = rand_r(&seed) % W1; c2 = rand_r(&seed) % W1;
                    if (c1 == c2) continue;
                    tmp = p1[c1]; p1[c1] = p1[c2]; p1[c2] = tmp;
                } else {
                    c1 = rand_r(&seed) % W2; c2 = rand_r(&seed) % W2;
                    if (c1 == c2) continue;
                    tmp = p2[c1]; p2[c1] = p2[c2]; p2[c2] = tmp;
                }

                invert_columnar(z_arr, W2, H2, p2, mid);
                invert_columnar(mid, W1, H1, p1, pt);
                float sc = eval_quad(pt);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    if (layer == 0) { p1[c2] = p1[c1]; p1[c1] = tmp; }
                    else { p2[c2] = p2[c1]; p2[c1] = tmp; }
                }

                temp *= cooling;
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_p1, p1, W1 * sizeof(int));
                memcpy(l_p2, p2, W2 * sizeof(int));
                invert_columnar(z_arr, W2, H2, p2, mid);
                invert_columnar(mid, W1, H1, p1, pt);
                for (int t = 0; t < N; t++) l_pt[t] = 'A' + pt[t];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_p1, l_p1, W1 * sizeof(int));
                memcpy(g_p2, l_p2, W2 * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] NEW RECORD: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("FINAL RESULT for Pair (42, 36) [%d restarts in %.3f s]\n", restarts, elapsed);
    printf("======================================================================\n");
    printf("Best Score: %.4f\n", global_best_sc);
    printf("Order 1 (W1=42): [");
    for (int i = 0; i < W1; i++) printf("%d%s", g_p1[i], i==W1-1?"":", ");
    printf("]\n");
    printf("Order 2 (W2=36): [");
    for (int i = 0; i < W2; i++) printf("%d%s", g_p2[i], i==W2-1?"":", ");
    printf("]\n\n");

    printf("Full Plaintext:\n%s\n\n", g_pt);

    printf("Plaintext layout in 12 rows of 42 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[43];
        memcpy(buf, g_pt + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }
}

int main(int argc, char **argv) {
    load_quads();
    init_z();

    int restarts = (argc > 1) ? atoi(argv[1]) : 1500;
    test_pair(restarts);

    return 0;
}

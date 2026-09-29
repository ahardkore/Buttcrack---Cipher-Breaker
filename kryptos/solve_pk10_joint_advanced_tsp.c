#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define W 42
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

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int c_idx[N];
static int alpha_to_std[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
    }
}

static const int Q7_PK[7] = {0, 22, 3, 3, 15, 0, 1};

static inline void compute_z(const int *q8, const int *q9, int *Z) {
    for (int i = 0; i < N; i++) {
        int k = (Q7_PK[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        Z[i] = alpha_to_std[p];
    }
}

static inline float eval_full(const int *Z, const int *perm) {
    int pt[N];
    int idx = 0;
    for (int r = 0; r < H; r++) {
        int base = r * W;
        for (int c = 0; c < W; c++) {
            pt[idx++] = Z[base + perm[c]];
        }
    }
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

static inline void apply_reverse(int *p, int i, int j) {
    while (i < j) {
        int t = p[i]; p[i] = p[j]; p[j] = t;
        i++; j--;
    }
}

static inline void apply_insert(int *p, int from, int to) {
    int val = p[from];
    if (from < to) {
        for (int k = from; k < to; k++) p[k] = p[k + 1];
    } else {
        for (int k = from; k > to; k--) p[k] = p[k - 1];
    }
    p[to] = val;
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 10000;

    printf("======================================================================\n");
    printf("PK10 Joint Advanced TSP Annealer (Clocks Q8, Q9 + W=42 TSP Operators)\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    int seed_q8[8] = {22, 15, 5, 9, 20, 6, 4, 6};
    int seed_q9[9] = {23, 2, 25, 22, 18, 9, 13, 13, 24};
    int seed_perm[W] = {
        30, 38, 21, 3, 25, 40, 17, 36, 12, 10,
        29, 33, 8, 41, 7, 32, 20, 0, 23, 34,
        19, 2, 22, 27, 6, 37, 31, 24, 39, 18,
        28, 35, 11, 13, 4, 26, 15, 5, 1, 14,
        16, 9
    };

    int init_Z[N];
    compute_z(seed_q8, seed_q9, init_Z);
    float global_best_sc = eval_full(init_Z, seed_perm);
    printf("Baseline Seed Score: %.4f\n\n", global_best_sc);

    int g_q8[8], g_q9[9], g_perm[W];
    memcpy(g_q8, seed_q8, 8 * sizeof(int));
    memcpy(g_q9, seed_q9, 9 * sizeof(int));
    memcpy(g_perm, seed_perm, W * sizeof(int));
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 7717 + omp_get_thread_num() * 5519;
        float loc_best_sc = global_best_sc;
        int l_q8[8], l_q9[9], l_perm[W];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 25)
        for (int rep = 0; rep < restarts; rep++) {
            int q8[8], q9[9], perm[W];
            memcpy(q8, g_q8, 8 * sizeof(int));
            memcpy(q9, g_q9, 9 * sizeof(int));
            memcpy(perm, g_perm, W * sizeof(int));

            if (rep > 0) {
                // Mutate clocks
                int p8 = rand_r(&seed) % 8;
                q8[p8] = (q8[p8] + rand_r(&seed) % 5 - 2 + 26) % 26;
                int p9 = rand_r(&seed) % 9;
                q9[p9] = (q9[p9] + rand_r(&seed) % 5 - 2 + 26) % 26;

                // Mutate perm
                int s = 1 + rand_r(&seed) % 4;
                for (int k = 0; k < s; k++) {
                    int c1 = rand_r(&seed) % W, c2 = rand_r(&seed) % W;
                    int t = perm[c1]; perm[c1] = perm[c2]; perm[c2] = t;
                }
            }

            int Z[N];
            compute_z(q8, q9, Z);
            float cur_sc = eval_full(Z, perm);

            float temp = 1.0f;
            float cooling = 0.999f;

            for (int step = 0; step < 2500; step++) {
                int op = rand_r(&seed) % 5;
                int old_v, new_v, pos, c1, c2, tmp;
                int backup_perm[W];

                if (op == 0) {
                    // Mutate Q8
                    pos = rand_r(&seed) % 8; old_v = q8[pos];
                    new_v = (old_v + 1 + rand_r(&seed) % 25) % 26;
                    q8[pos] = new_v;
                    compute_z(q8, q9, Z);
                } else if (op == 1) {
                    // Mutate Q9
                    pos = rand_r(&seed) % 9; old_v = q9[pos];
                    new_v = (old_v + 1 + rand_r(&seed) % 25) % 26;
                    q9[pos] = new_v;
                    compute_z(q8, q9, Z);
                } else if (op == 2) {
                    // Single swap
                    c1 = rand_r(&seed) % W; c2 = rand_r(&seed) % W;
                    if (c1 == c2) continue;
                    tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;
                } else if (op == 3) {
                    // Segment reversal
                    c1 = rand_r(&seed) % W; c2 = rand_r(&seed) % W;
                    if (c1 == c2) continue;
                    memcpy(backup_perm, perm, W * sizeof(int));
                    int lo = c1 < c2 ? c1 : c2;
                    int hi = c1 < c2 ? c2 : c1;
                    apply_reverse(perm, lo, hi);
                } else {
                    // Block insertion
                    c1 = rand_r(&seed) % W; c2 = rand_r(&seed) % W;
                    if (c1 == c2) continue;
                    memcpy(backup_perm, perm, W * sizeof(int));
                    apply_insert(perm, c1, c2);
                }

                float sc = eval_full(Z, perm);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    if (op == 0) { q8[pos] = old_v; compute_z(q8, q9, Z); }
                    else if (op == 1) { q9[pos] = old_v; compute_z(q8, q9, Z); }
                    else if (op == 2) { perm[c2] = perm[c1]; perm[c1] = tmp; }
                    else { memcpy(perm, backup_perm, W * sizeof(int)); }
                }

                temp *= cooling;
            }

            // Polish with 2-opt swaps and reversals on columns (Z stays fixed)
            int imp = 1;
            while (imp) {
                imp = 0;
                for (int i = 0; i < W - 1; i++) {
                    for (int j = i + 1; j < W; j++) {
                        int t = perm[i]; perm[i] = perm[j]; perm[j] = t;
                        float sc = eval_full(Z, perm);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            imp = 1;
                        } else {
                            perm[j] = perm[i]; perm[i] = t;
                        }

                        apply_reverse(perm, i, j);
                        sc = eval_full(Z, perm);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            imp = 1;
                        } else {
                            apply_reverse(perm, i, j);
                        }
                    }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_q8, q8, 8 * sizeof(int));
                memcpy(l_q9, q9, 9 * sizeof(int));
                memcpy(l_perm, perm, W * sizeof(int));

                int idx = 0;
                for (int r = 0; r < H; r++) {
                    int base = r * W;
                    for (int c = 0; c < W; c++) {
                        l_pt[idx++] = 'A' + Z[base + perm[c]];
                    }
                }
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_q8, l_q8, 8 * sizeof(int));
                memcpy(g_q9, l_q9, 9 * sizeof(int));
                memcpy(g_perm, l_perm, W * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] JOINT TSP NEW RECORD: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  Q8: [");
                for (int i = 0; i < 8; i++) printf("%d, ", g_q8[i]);
                printf("]\n  Q9: [");
                for (int i = 0; i < 9; i++) printf("%d, ", g_q9[i]);
                printf("]\n  Order: [");
                for (int i = 0; i < 10; i++) printf("%d, ", g_perm[i]);
                printf("...]\n");
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("JOINT TSP COMPLETED (%d restarts in %.3f s)\n", restarts, elapsed);
    printf("======================================================================\n");
    printf("Best Score: %.4f\n", global_best_sc);
    printf("Q8: [");
    for (int i = 0; i < 8; i++) printf("%d%s", g_q8[i], i==7?"":", ");
    printf("] (KR: ");
    for (int i = 0; i < 8; i++) printf("%c", KRYPTOS[g_q8[i]]);
    printf(")\n");
    printf("Q9: [");
    for (int i = 0; i < 9; i++) printf("%d%s", g_q9[i], i==8?"":", ");
    printf("] (KR: ");
    for (int i = 0; i < 9; i++) printf("%c", KRYPTOS[g_q9[i]]);
    printf(")\n");
    printf("Order (len 42): [");
    for (int i = 0; i < W; i++) printf("%d%s", g_perm[i], i==W-1?"":", ");
    printf("]\n\n");

    printf("Full Plaintext:\n%s\n\n", g_pt);

    printf("Plaintext layout in 12 rows of 42 chars:\n");
    for (int r = 0; r < H; r++) {
        char buf[W + 1];
        memcpy(buf, g_pt + r * W, W);
        buf[W] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}

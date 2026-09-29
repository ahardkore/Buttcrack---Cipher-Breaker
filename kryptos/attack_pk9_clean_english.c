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

// Allowed shifts for each of the 28 phases that produce 0 rare letters
static int allowed_shifts[28][26];
static int num_allowed[28];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK9_RAW[i]];

    // Precompute allowed shifts with NO rare letters (J, Q, X, Z in std: 9, 16, 23, 25)
    for (int j = 0; j < 28; j++) {
        num_allowed[j] = 0;
        for (int s = 0; s < 26; s++) {
            int has_rare = 0;
            for (int i = j; i < N; i += 28) {
                int p_kr = (ct_kr[i] - s + 26) % 26;
                int p_std = k2std[p_kr];
                if (p_std == 9 || p_std == 16 || p_std == 23 || p_std == 25) {
                    has_rare = 1;
                    break;
                }
            }
            if (!has_rare) {
                allowed_shifts[j][num_allowed[j]++] = s;
            }
        }
    }
}

static inline void invert_col(const int *src, int w, int h, const int *perm, int *dst) {
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < h; r++) {
            dst[r * w + col] = src[idx++];
        }
    }
}

static inline float score_text(const int *txt, int len) {
    float sc = 0.0f;
    for (int i = 0; i < len - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (len - 3);
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 5000;

    printf("======================================================================\n");
    printf("PK9 Attack: Rare-Letter-Suppressed Keystream & Permutation Optimization\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    for (int j = 0; j < 28; j++) {
        printf("Phase %2d: %d clean shifts allowed\n", j, num_allowed[j]);
    }
    printf("\n");

    float global_best_sc = -999.0f;
    int best_s[28], best_p1[18], best_p2[8];
    char best_pt[N + 1];

    const int init_p1[18] = {5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6};
    const int init_p2[8] = {7, 0, 5, 2, 4, 3, 6, 1};

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 76543 + omp_get_thread_num() * 3333;
        float loc_best = -999.0f;
        int loc_s[28], loc_p1[18], loc_p2[8];
        char loc_pt[N + 1];

        #pragma omp for schedule(dynamic, 10)
        for (int rep = 0; rep < restarts; rep++) {
            int s[28], p1[18], p2[8];
            for (int j = 0; j < 28; j++) {
                if (num_allowed[j] > 0) {
                    s[j] = allowed_shifts[j][rand_r(&seed) % num_allowed[j]];
                } else {
                    s[j] = rand_r(&seed) % 26;
                }
            }
            memcpy(p1, init_p1, 18 * sizeof(int));
            memcpy(p2, init_p2, 8 * sizeof(int));

            // slight permutation perturbation
            int k1 = rand_r(&seed) % 18, k2 = rand_r(&seed) % 18;
            int t = p1[k1]; p1[k1] = p1[k2]; p1[k2] = t;

            int Z_loc[N], mid[N], pt[N];
            for (int i = 0; i < N; i++) {
                int shift = s[i % 28];
                int p_kr = (ct_kr[i] - shift + 26) % 26;
                Z_loc[i] = k2std[p_kr];
            }
            invert_col(Z_loc, W2, H2, p2, mid);
            invert_col(mid, W1, H1, p1, pt);
            float cur_sc = score_text(pt, N);

            // Simulated Annealing
            float temp = 0.5f;
            float cooling = 0.995f;

            for (int step = 0; step < 2500; step++) {
                int move = rand_r(&seed) % 40;

                if (move < 28) {
                    // Change shift s[move]
                    int pos = move;
                    if (num_allowed[pos] > 1) {
                        int old_v = s[pos];
                        int new_v = allowed_shifts[pos][rand_r(&seed) % num_allowed[pos]];
                        if (new_v != old_v) {
                            s[pos] = new_v;
                            // Update Z_loc at indices i % 28 == pos
                            for (int i = pos; i < N; i += 28) {
                                int p_kr = (ct_kr[i] - new_v + 26) % 26;
                                Z_loc[i] = k2std[p_kr];
                            }
                            invert_col(Z_loc, W2, H2, p2, mid);
                            invert_col(mid, W1, H1, p1, pt);
                            float sc = score_text(pt, N);
                            float delta = sc - cur_sc;
                            if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                                cur_sc = sc;
                            } else {
                                s[pos] = old_v;
                                for (int i = pos; i < N; i += 28) {
                                    int p_kr = (ct_kr[i] - old_v + 26) % 26;
                                    Z_loc[i] = k2std[p_kr];
                                }
                            }
                        }
                    }
                } else if (move < 36) {
                    // Swap in p1
                    int i = rand_r(&seed) % 18;
                    int j = rand_r(&seed) % 18;
                    if (i != j) {
                        int t = p1[i]; p1[i] = p1[j]; p1[j] = t;
                        invert_col(mid, W1, H1, p1, pt);
                        float sc = score_text(pt, N);
                        float delta = sc - cur_sc;
                        if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                            cur_sc = sc;
                        } else {
                            p1[j] = p1[i]; p1[i] = t;
                        }
                    }
                } else {
                    // Swap in p2
                    int i = rand_r(&seed) % 8;
                    int j = rand_r(&seed) % 8;
                    if (i != j) {
                        int t = p2[i]; p2[i] = p2[j]; p2[j] = t;
                        invert_col(Z_loc, W2, H2, p2, mid);
                        invert_col(mid, W1, H1, p1, pt);
                        float sc = score_text(pt, N);
                        float delta = sc - cur_sc;
                        if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                            cur_sc = sc;
                        } else {
                            p2[j] = p2[i]; p2[i] = t;
                        }
                    }
                }

                temp *= cooling;
            }

            if (cur_sc > loc_best) {
                loc_best = cur_sc;
                memcpy(loc_s, s, 28 * sizeof(int));
                memcpy(loc_p1, p1, 18 * sizeof(int));
                memcpy(loc_p2, p2, 8 * sizeof(int));
                for (int i = 0; i < N; i++) loc_pt[i] = 'A' + pt[i];
                loc_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best > global_best_sc) {
                global_best_sc = loc_best;
                memcpy(best_s, loc_s, 28 * sizeof(int));
                memcpy(best_p1, loc_p1, 18 * sizeof(int));
                memcpy(best_p2, loc_p2, 8 * sizeof(int));
                strcpy(best_pt, loc_pt);
                printf("[Thread %d] Record: Score=%.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  Shifts: [");
                for (int i = 0; i < 28; i++) printf("%d%s", best_s[i], i==27?"":", ");
                printf("]\n  PT: %.60s...\n\n", best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("ATTACK COMPLETED in %.2f s | Best Score: %.4f\n", elapsed, global_best_sc);
    printf("======================================================================\n");
    printf("Proven Shifts: [");
    for (int i = 0; i < 28; i++) printf("%d%s", best_s[i], i==27?"":", ");
    printf("]\n\nFull Plaintext:\n%s\n\n", best_pt);

    printf("Plaintext layout in 8 rows of 18 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[W1 + 1];
        memcpy(buf, best_pt + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}

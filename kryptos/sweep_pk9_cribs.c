#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <omp.h>

static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *ALPH_S = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static int inv13[13] = {0, 1, 7, 9, 10, 8, 11, 2, 5, 3, 4, 6, 12};

static float quad_table[26][26][26][26];
static int k_to_std[26];
static int std_to_k[26];

static const char *M_STR = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";
static const char *C_STR = "KSYAWFEYYOISZGEUFBTLAYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

typedef struct {
    uint16_t basis2[16];
    int val2[16];
    int has2[16];

    int basis13[16][16];
    int val13[16];
    int has13[16];
} System457;

static inline void sys457_init(System457 *sys) {
    memset(sys, 0, sizeof(System457));
}

static inline int sys457_add(System457 *sys, int pos, int rhs26) {
    int rhs2 = rhs26 & 1;
    int rhs13 = rhs26 % 13;

    uint16_t mask2 = (1 << (pos % 4)) | (1 << (4 + (pos % 5))) | (1 << (9 + (pos % 7)));
    int row13[16] = {0};
    row13[pos % 4] = 1;
    row13[4 + (pos % 5)] = 1;
    row13[9 + (pos % 7)] = 1;

    for (int p = 0; p < 16; p++) {
        if (mask2 & (1 << p)) {
            if (sys->has2[p]) {
                mask2 ^= sys->basis2[p];
                rhs2 ^= sys->val2[p];
            } else {
                sys->basis2[p] = mask2;
                sys->val2[p] = rhs2;
                sys->has2[p] = 1;
                break;
            }
        }
    }
    if (mask2 == 0 && rhs2 != 0) return 0;

    for (int p = 0; p < 16; p++) {
        int factor = row13[p];
        if (factor != 0) {
            if (sys->has13[p]) {
                for (int j = p; j < 16; j++) {
                    row13[j] = (row13[j] - factor * sys->basis13[p][j]) % 13;
                    if (row13[j] < 0) row13[j] += 13;
                }
                rhs13 = (rhs13 - factor * sys->val13[p]) % 13;
                if (rhs13 < 0) rhs13 += 13;
            } else {
                int inv = inv13[factor];
                for (int j = p; j < 16; j++) {
                    sys->basis13[p][j] = (row13[j] * inv) % 13;
                }
                sys->val13[p] = (rhs13 * inv) % 13;
                sys->has13[p] = 1;
                break;
            }
        }
    }
    for (int j = 0; j < 16; j++) if (row13[j] != 0) return 1;
    return rhs13 == 0;
}

static inline int sys457_eval(const System457 *sys, int pos, int *out_k) {
    uint16_t mask2 = (1 << (pos % 4)) | (1 << (4 + (pos % 5))) | (1 << (9 + (pos % 7)));
    int v2 = 0;
    for (int p = 0; p < 16; p++) {
        if (mask2 & (1 << p)) {
            if (!sys->has2[p]) return 0;
            mask2 ^= sys->basis2[p];
            v2 ^= sys->val2[p];
        }
    }

    int row13[16] = {0};
    row13[pos % 4] = 1;
    row13[4 + (pos % 5)] = 1;
    row13[9 + (pos % 7)] = 1;
    int v13 = 0;
    for (int p = 0; p < 16; p++) {
        int factor = row13[p];
        if (factor != 0) {
            if (!sys->has13[p]) return 0;
            for (int j = p; j < 16; j++) {
                row13[j] = (row13[j] - factor * sys->basis13[p][j]) % 13;
                if (row13[j] < 0) row13[j] += 13;
            }
            v13 = (v13 + factor * sys->val13[p]) % 13;
        }
    }
    *out_k = (13 * v2 + 14 * v13) % 26;
    return 1;
}

// Load quadgrams
void init_quads() {
    for (int i = 0; i < 26; i++) {
        for (int j = 0; j < 26; j++) {
            for (int k = 0; k < 26; k++) {
                for (int l = 0; l < 26; l++) {
                    quad_table[i][j][k][l] = -9.0f;
                }
            }
        }
    }
    FILE *f = fopen("/home/user/english_quads.tsv", "r");
    if (!f) { fprintf(stderr, "Cannot open quads\n"); exit(1); }
    char q[16];
    float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int c0 = q[0]-'A', c1 = q[1]-'A', c2 = q[2]-'A', c3 = q[3]-'A';
            if (c0>=0&&c0<26&&c1>=0&&c1<26&&c2>=0&&c2<26&&c3>=0&&c3<26) {
                quad_table[c0][c1][c2][c3] = sc;
            }
        }
    }
    fclose(f);

    for (int i = 0; i < 26; i++) {
        int std = ALPH_K[i] - 'A';
        k_to_std[i] = std;
        std_to_k[std] = i;
    }
}

// Load cribs
static char **crib_list = NULL;
static int n_cribs = 0;

void load_cribs() {
    FILE *f = fopen("/home/user/whitesmith_cribs.txt", "r");
    if (!f) { fprintf(stderr, "Cannot open cribs\n"); exit(1); }
    crib_list = malloc(20000 * sizeof(char*));
    char buf[64];
    while (fscanf(f, "%63s", buf) == 1) {
        crib_list[n_cribs] = strdup(buf);
        n_cribs++;
    }
    fclose(f);
    printf("Loaded %d candidate cribs.\n", n_cribs);
}

void test_target(const char *target_str, int is_kryptos, const char *target_name) {
    printf("\n=== Running Crib Sweep on %s (Alphabet: %s) ===\n",
           target_name, is_kryptos ? "KRYPTOS" : "STANDARD");

    int ct[144];
    for (int i = 0; i < 144; i++) {
        if (is_kryptos) ct[i] = std_to_k[target_str[i] - 'A'];
        else ct[i] = target_str[i] - 'A';
    }

    float global_best_sc = -999.0f;
    char global_best_hit[128] = "";
    char global_best_pt[150] = "";

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_best_hit[128] = "";
        char local_best_pt[150] = "";

        #pragma omp for schedule(dynamic)
        for (int c_idx = 0; c_idx < n_cribs; c_idx++) {
            const char *crib = crib_list[c_idx];
            int clen = strlen(crib);
            int crib_indices[32];
            for (int j = 0; j < clen; j++) {
                if (is_kryptos) crib_indices[j] = std_to_k[crib[j] - 'A'];
                else crib_indices[j] = crib[j] - 'A';
            }

            for (int pos = 0; pos <= 144 - clen; pos++) {
                System457 sys;
                sys457_init(&sys);

                int ok = 1;
                for (int j = 0; j < clen; j++) {
                    int rhs = (ct[pos + j] - crib_indices[j] + 26) % 26;
                    if (!sys457_add(&sys, pos + j, rhs)) {
                        ok = 0; break;
                    }
                }
                if (!ok) continue;

                // Check if fully determined
                int pt_std[144];
                int fully_det = 1;
                for (int i = 0; i < 144; i++) {
                    int k;
                    if (!sys457_eval(&sys, i, &k)) {
                        fully_det = 0; break;
                    }
                    int p_idx = (ct[i] - k + 26) % 26;
                    if (is_kryptos) pt_std[i] = k_to_std[p_idx];
                    else pt_std[i] = p_idx;
                }
                if (!fully_det) continue;

                // Score with quadgrams
                float sc = 0.0f;
                for (int i = 0; i < 141; i++) {
                    sc += quad_table[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
                }
                sc /= 141.0f;

                if (sc > local_best_sc) {
                    local_best_sc = sc;
                    sprintf(local_best_hit, "%s at pos %d", crib, pos);
                    for (int i = 0; i < 144; i++) local_best_pt[i] = pt_std[i] + 'A';
                    local_best_pt[144] = '\0';
                }

                if (sc > -5.8f) {
                    #pragma omp critical
                    {
                        printf("!!! HIGH SCORE HIT !!! sc=%.3f | %s at pos %d\n", sc, crib, pos);
                        char hit_pt[150];
                        for (int i = 0; i < 144; i++) hit_pt[i] = pt_std[i] + 'A';
                        hit_pt[144] = '\0';
                        printf("PT: %s\n", hit_pt);
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(global_best_hit, local_best_hit);
                strcpy(global_best_pt, local_best_pt);
                printf("  [New Best] sc=%.3f | %s | PT: %.45s...\n",
                       global_best_sc, global_best_hit, global_best_pt);
            }
        }
    }

    printf("Sweep Finished on %s (%s). Best: sc=%.3f (%s)\n  PT: %s\n",
           target_name, is_kryptos ? "KRYPTOS" : "STANDARD",
           global_best_sc, global_best_hit, global_best_pt);
}

int main() {
    init_quads();
    load_cribs();

    // 1. Stream M (KRYPTOS)
    test_target(M_STR, 1, "Stream M");

    // 2. Stream M (STANDARD)
    test_target(M_STR, 0, "Stream M");

    // 3. Raw C (KRYPTOS)
    test_target(C_STR, 1, "Raw C");

    // 4. Raw C (STANDARD)
    test_target(C_STR, 0, "Raw C");

    return 0;
}

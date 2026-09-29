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

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";

static int ct_kr[N];
static int ct_std[N];
static int k2std[26];
static int hpos[256];

#define NUM_VARS 24 // q7: 0..6, q8: 7..14, q9: 15..23

static inline float score_pt(const int *pt_std) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return s / (N - 3);
}

void compute_pt(const int *vars, int *pt_std, int mode) {
    for (int t = 0; t < N; t++) {
        int k = (vars[t % 7] + vars[7 + (t % 8)] + vars[15 + (t % 9)]) % 26;
        if (mode == 0) {
            int p_kr = (ct_kr[t] - k + 26) % 26;
            pt_std[t] = k2std[p_kr];
        } else {
            pt_std[t] = (ct_std[t] - k + 26) % 26;
        }
    }
}

float climb_clocks(int *vars, int mode, unsigned int *seed) {
    int pt[N];
    compute_pt(vars, pt, mode);
    float cur_sc = score_pt(pt);

    // Fast SA (2,500 steps)
    float T = 2.0f;
    float cooling = 0.999f;
    for (int step = 0; step < 2500; step++) {
        T *= cooling;
        int vi = rand_r(seed) % NUM_VARS;
        if (vi == 0 || vi == 7) continue; // fix gauges: vars[0]=0, vars[7]=0

        int old_v = vars[vi];
        int new_v = (old_v + 1 + rand_r(seed) % 25) % 26;
        vars[vi] = new_v;

        compute_pt(vars, pt, mode);
        float sc = score_pt(pt);
        float delta = sc - cur_sc;

        if (delta > 0 || (float)rand_r(seed) / RAND_MAX < expf(delta / T)) {
            cur_sc = sc;
        } else {
            vars[vi] = old_v;
        }
    }

    // 1-Opt Greedy Polish
    int improved = 1;
    int passes = 0;
    while (improved && passes < 12) {
        improved = 0;
        passes++;
        for (int vi = 0; vi < NUM_VARS; vi++) {
            if (vi == 0 || vi == 7) continue;
            int old_v = vars[vi];
            int best_v = old_v;
            float best_s = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == old_v) continue;
                vars[vi] = v;
                compute_pt(vars, pt, mode);
                float sc = score_pt(pt);
                if (sc > best_s) {
                    best_s = sc;
                    best_v = v;
                }
            }
            vars[vi] = best_v;
            if (best_v != old_v) {
                cur_sc = best_s;
                improved = 1;
            }
        }
    }

    // 2-Opt Coupled Polish
    improved = 1;
    passes = 0;
    while (improved && passes < 6) {
        improved = 0;
        passes++;
        for (int v1 = 0; v1 < NUM_VARS - 1; v1++) {
            if (v1 == 0 || v1 == 7) continue;
            for (int v2 = v1 + 1; v2 < NUM_VARS; v2++) {
                if (v2 == 0 || v2 == 7) continue;

                int old1 = vars[v1];
                int old2 = vars[v2];
                int best_d = 0;
                float best_s = cur_sc;

                for (int d = 1; d < 26; d++) {
                    vars[v1] = (old1 + d) % 26;
                    vars[v2] = (old2 - d + 26) % 26;
                    compute_pt(vars, pt, mode);
                    float sc = score_pt(pt);
                    if (sc > best_s) {
                        best_s = sc;
                        best_d = d;
                    }
                }
                if (best_d != 0) {
                    vars[v1] = (old1 + best_d) % 26;
                    vars[v2] = (old2 - best_d + 26) % 26;
                    cur_sc = best_s;
                    improved = 1;
                } else {
                    vars[v1] = old1;
                    vars[v2] = old2;
                }
            }
        }
    }

    return cur_sc;
}

int main() {
    load_quads();

    // Load PK10 ciphertext
    FILE *f = fopen("pk_all_ciphertexts.json", "r");
    if (!f) { printf("Cannot open pk_all_ciphertexts.json\n"); exit(1); }
    char buf[4096];
    size_t len = fread(buf, 1, sizeof(buf) - 1, f);
    buf[len] = '\0';
    fclose(f);

    char *p = strstr(buf, "\"PK10\": \"");
    if (!p) { printf("PK10 not found in json\n"); exit(1); }
    p += 9;
    char pk10_raw[N + 1];
    for (int i = 0; i < N; i++) pk10_raw[i] = p[i];
    pk10_raw[N] = '\0';

    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)pk10_raw[i]];
        ct_std[i] = pk10_raw[i] - 'A';
    }

    printf("Starting Triple CRT Sum-Clock (7, 8, 9) Solver on PK10 (N=504)...\n");

    for (int mode = 0; mode < 2; mode++) {
        printf("\n=========================================\n");
        printf("Mode: %s\n", mode == 0 ? "Quagmire III (KRYPTOS)" : "Standard Vigenere (A-Z)");
        printf("=========================================\n");

        double t0 = omp_get_wtime();
        float global_best_sc = -999.0f;
        char global_best_pt[N + 1] = "";
        int best_vars[NUM_VARS];

        #define RESTARTS 200

        #pragma omp parallel
        {
            float loc_best = -999.0f;
            char loc_pt[N + 1] = "";
            int loc_vars[NUM_VARS];
            unsigned int seed = 88888 + omp_get_thread_num() * 1111;

            #pragma omp for schedule(dynamic, 10)
            for (int r = 0; r < RESTARTS; r++) {
                int cur_vars[NUM_VARS];
                for (int i = 0; i < NUM_VARS; i++) {
                    if (i == 0 || i == 7) cur_vars[i] = 0;
                    else cur_vars[i] = rand_r(&seed) % 26;
                }

                float sc = climb_clocks(cur_vars, mode, &seed);

                if (sc > -5.3f) {
                    #pragma omp critical
                    {
                        int pt[N];
                        compute_pt(cur_vars, pt, mode);
                        char pt_str[N + 1];
                        for (int t = 0; t < N; t++) pt_str[t] = 'A' + pt[t];
                        pt_str[N] = '\0';
                        printf(">>> BREAKTHROUGH CANDIDATE ON PK10! Score: %.4f <<<\n", sc);
                        printf("  PT: %.80s...\n\n", pt_str);
                    }
                }

                if (sc > loc_best) {
                    loc_best = sc;
                    memcpy(loc_vars, cur_vars, NUM_VARS * sizeof(int));
                    int pt[N];
                    compute_pt(cur_vars, pt, mode);
                    for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                    loc_pt[N] = '\0';
                }
            }

            #pragma omp critical
            {
                if (loc_best > global_best_sc) {
                    global_best_sc = loc_best;
                    memcpy(best_vars, loc_vars, NUM_VARS * sizeof(int));
                    strcpy(global_best_pt, loc_pt);
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        printf("Completed %d restarts in %.3f s\n", RESTARTS, elapsed);
        printf("Global Best Score: %.4f\n", global_best_sc);
        printf("q7: "); for (int i = 0; i < 7; i++) printf("%d ", best_vars[i]); printf("\n");
        printf("q8: "); for (int i = 7; i < 15; i++) printf("%d ", best_vars[i]); printf("\n");
        printf("q9: "); for (int i = 15; i < 24; i++) printf("%d ", best_vars[i]); printf("\n");
        printf("PT (first 100 chars): %.100s\n", global_best_pt);
    }

    return 0;
}

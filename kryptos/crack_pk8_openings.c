#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const int ps[4] = {4, 5, 6, 7};
static int c_idx[N];
static int alpha_to_std[26];
static int char_to_k[256];
static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) exit(1);
    char q[16]; float sc;
    while (fscanf(f, "%s %f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

void init_tables() {
    for (int i = 0; i < 256; i++) char_to_k[i] = -1;
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
        char_to_k[(unsigned char)KRYPTOS[i]] = i;
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = char_to_k[(unsigned char)PK8_CT[i]];
    }
}

static int rows[N][22];

void init_rows() {
    for (int pos = 0; pos < N; pos++) {
        memset(rows[pos], 0, 22 * sizeof(int));
        rows[pos][pos % 4] = 1;
        rows[pos][4 + (pos % 5)] = 1;
        rows[pos][9 + (pos % 6)] = 1;
        rows[pos][15 + (pos % 7)] = 1;
    }
}

int inv_mod(int a, int m) {
    a = (a % m + m) % m;
    for (int x = 1; x < m; x++) {
        if ((a * x) % m == 1) return x;
    }
    return 1;
}

typedef struct {
    int basis[22][22];
    int rhs[22];
    int has_pivot[22];
    int p;
} Sys;

void init_sys(Sys *s, int p) {
    memset(s, 0, sizeof(Sys));
    s->p = p;
}

int add_eq(Sys *s, const int *in_row, int in_rhs) {
    int row[22];
    for (int i = 0; i < 22; i++) row[i] = (in_row[i] % s->p + s->p) % s->p;
    int val = (in_rhs % s->p + s->p) % s->p;

    for (int i = 0; i < 22; i++) {
        if (s->has_pivot[i] && row[i] != 0) {
            int factor = row[i];
            for (int j = 0; j < 22; j++) {
                row[j] = (row[j] - factor * s->basis[i][j]) % s->p;
                if (row[j] < 0) row[j] += s->p;
            }
            val = (val - factor * s->rhs[i]) % s->p;
            if (val < 0) val += s->p;
        }
    }

    int pivot = -1;
    for (int i = 0; i < 22; i++) {
        if (row[i] != 0) { pivot = i; break; }
    }

    if (pivot == -1) return val == 0;

    int inv = inv_mod(row[pivot], s->p);
    for (int j = 0; j < 22; j++) {
        s->basis[pivot][j] = (row[j] * inv) % s->p;
    }
    s->rhs[pivot] = (val * inv) % s->p;
    s->has_pivot[pivot] = 1;
    return 1;
}

int solve_rep(const Sys *s, int *out_vec) {
    for (int i = 0; i < 22; i++) out_vec[i] = 0;
    for (int i = 21; i >= 0; i--) {
        if (s->has_pivot[i]) {
            int sum = 0;
            for (int j = i + 1; j < 22; j++) {
                sum = (sum + s->basis[i][j] * out_vec[j]) % s->p;
            }
            out_vec[i] = (s->rhs[i] - sum + s->p * 100) % s->p;
        }
    }
    return 1;
}

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

float eval_crib(int start_pos, const char *crib, char *full_pt_out) {
    int clen = strlen(crib);
    Sys s2, s13;
    init_sys(&s2, 2);
    init_sys(&s13, 13);

    for (int i = 0; i < clen; i++) {
        int pos = start_pos + i;
        int p_idx = char_to_k[(unsigned char)crib[i]];
        if (p_idx == -1) return -999.0f;
        int rhs = (c_idx[pos] - p_idx + 26) % 26;
        if (!add_eq(&s2, rows[pos], rhs)) return -999.0f;
        if (!add_eq(&s13, rows[pos], rhs)) return -999.0f;
    }

    int x2[22], x13[22], rep[22];
    solve_rep(&s2, x2);
    solve_rep(&s13, x13);
    for (int i = 0; i < 22; i++) {
        rep[i] = (13 * x2[i] + 14 * x13[i]) % 26;
    }

    int pt[N];
    for (int i = 0; i < N; i++) {
        int k = (rep[i % 4] + rep[4 + (i % 5)] + rep[9 + (i % 6)] + rep[15 + (i % 7)]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        pt[i] = alpha_to_std[p];
        if (full_pt_out) full_pt_out[i] = 'A' + pt[i];
    }
    if (full_pt_out) full_pt_out[N] = '\0';

    return score_plain(pt);
}

int main() {
    load_quadgrams();
    init_tables();
    init_rows();

    printf("Preloading cribs from pk8_narrative_cribs.txt...\n");
    FILE *f = fopen("pk8_narrative_cribs.txt", "r");
    if (!f) { printf("Failed to open pk8_narrative_cribs.txt\n"); return 1; }

    static char cribs[35000][32];
    int n_cribs = 0;
    char line[64];
    while (fgets(line, sizeof(line), f) && n_cribs < 35000) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == 18) {
            strcpy(cribs[n_cribs++], w);
        }
    }
    fclose(f);
    printf("Loaded %d 18-character cribs. Testing pos 0...\n", n_cribs);

    float global_best_sc = -999.0f;
    char global_best_crib[32] = "";
    char global_best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_best_crib[32] = "";
        char local_best_pt[N + 1] = "";

        #pragma omp for schedule(dynamic, 100)
        for (int i = 0; i < n_cribs; i++) {
            char pt[N + 1];
            float sc = eval_crib(0, cribs[i], pt);
            if (sc > -6.0f) {
                #pragma omp critical
                {
                    printf(">>> HIGH SCORING CANDIDATE: Score %.4f | Crib: %s <<<\n", sc, cribs[i]);
                    printf("PT: %.100s...\n\n", pt);
                    fflush(stdout);
                }
            }
            if (sc > local_best_sc) {
                local_best_sc = sc;
                strcpy(local_best_crib, cribs[i]);
                strcpy(local_best_pt, pt);
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(global_best_crib, local_best_crib);
                strcpy(global_best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Sweep complete in %.3f s (%d cribs evaluated, %.1f cribs/s).\n",
           elapsed, n_cribs, n_cribs / elapsed);
    printf("Best Score = %.4f | Crib: %s\n", global_best_sc, global_best_crib);
    printf("Plaintext: %s\n", global_best_pt);

    return 0;
}

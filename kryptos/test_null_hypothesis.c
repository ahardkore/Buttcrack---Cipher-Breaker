#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int kr_to_std[26];
static int std_to_kr[26];
static float quad_table[26][26][26][26];
static double log_monogram[26];

void load_models() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) exit(1);
    char q[16]; double cnt; double total = 0;
    while (fscanf(f, "%s %lf", q, &cnt) == 2) if (strlen(q) == 4) total += cnt;
    rewind(f);
    double mono_counts[26] = {0}, mono_tot = 0;
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quad_table[a][b][c][d] = (float)log10((cnt + 0.01) / total);
                mono_counts[a] += cnt; mono_counts[b] += cnt; mono_counts[c] += cnt; mono_counts[d] += cnt;
                mono_tot += 4 * cnt;
            }
        }
    }
    fclose(f);

    for (int a = 0; a < 26; a++) {
        log_monogram[a] = log10((mono_counts[a] + 0.1) / mono_tot);
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
}

void col_decrypt(const int *in, const int *order, int *out, int w, int h) {
    int grid[H][W];
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = order[c_idx];
        for (int r = 0; r < h; r++) grid[r][col] = in[idx++];
    }
    idx = 0;
    for (int r = 0; r < h; r++)
        for (int c = 0; c < w; c++) out[idx++] = grid[r][c];
}

static inline float score_quadgrams(const int *txt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return s / (N - 3);
}

static inline void get_mapping(const int *o1, const int *o2, int *pt_to_z2) {
    int identity[N]; for (int j = 0; j < N; j++) identity[j] = j;
    int after2[N];
    col_decrypt(identity, o2, after2, W, H);
    col_decrypt(after2, o1, pt_to_z2, W, H);
}

static inline void decrypt_with_shifts(const int *ct, const int *pt_to_z2, const int *shifts, int *pt) {
    for (int t = 0; t < N; t++) {
        int pos = pt_to_z2[t];
        int sh = shifts[pos % 28];
        int c_val = ct[pos];
        int p_val = (sh - c_val + 26) % 26;
        pt[t] = kr_to_std[p_val];
    }
}

float polish_shifts_quadgram(const int *ct, const int *pt_to_z2, int *shifts, int *pt) {
    decrypt_with_shifts(ct, pt_to_z2, shifts, pt);
    float cur_sc = score_quadgrams(pt);

    int improved = 1;
    int passes = 0;
    while (improved && passes < 10) {
        improved = 0;
        passes++;
        for (int s = 0; s < 28; s++) {
            int orig_val = shifts[s];
            int best_val = orig_val;
            float best_sc = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == orig_val) continue;
                shifts[s] = v;
                int test_pt[N];
                decrypt_with_shifts(ct, pt_to_z2, shifts, test_pt);
                float sc = score_quadgrams(test_pt);
                if (sc > best_sc) {
                    best_sc = sc;
                    best_val = v;
                }
            }
            if (best_val != orig_val) {
                shifts[s] = best_val;
                cur_sc = best_sc;
                improved = 1;
            } else {
                shifts[s] = orig_val;
            }
        }
    }
    decrypt_with_shifts(ct, pt_to_z2, shifts, pt);
    return cur_sc;
}

int main() {
    load_models();
    srand(42);

    int random_ct[N];
    for (int i = 0; i < N; i++) random_ct[i] = rand() % 26;

    int o1[W] = {0,1,2,3,4,5,6,7,8,9,10,11};
    int o2[W] = {0,1,2,3,4,5,6,7,8,9,10,11};
    int pt_to_z2[N];
    get_mapping(o1, o2, pt_to_z2);

    int shifts[28];
    for (int s = 0; s < 28; s++) shifts[s] = rand() % 26;

    int pt[N];
    float sc = polish_shifts_quadgram(random_ct, pt_to_z2, shifts, pt);

    printf("NULL HYPOTHESIS TEST:\n");
    printf("Score on pure RANDOM text with 28 shifts polished: %.4f\n", sc);
    char buf[N+1];
    for (int i = 0; i < N; i++) buf[i] = pt[i] + 'A';
    buf[N] = 0;
    printf("Plaintext on RANDOM: %s\n", buf);

    return 0;
}

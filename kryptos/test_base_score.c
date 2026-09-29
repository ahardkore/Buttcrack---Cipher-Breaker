#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int kr_to_std[26];
static int std_to_kr[26];
static float quad_table[26][26][26][26];

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
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26)
                quad_table[a][b][c][d] = (float)log10((cnt + 0.01) / total);
        }
    }
    fclose(f);

    for (int a = 0; a < 26; a++) {
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
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

int main() {
    load_models();
    int o1[W] = {3, 4, 11, 10, 6, 1, 8, 7, 9, 0, 5, 2};
    int o2[W] = {10, 9, 11, 2, 6, 4, 3, 1, 7, 5, 0, 8};
    int shifts[28] = {21, 1, 3, 13, 4, 17, 16, 6, 21, 19, 6, 18, 9, 24, 8, 25, 18, 18, 19, 2, 11, 15, 14, 21, 19, 25, 13, 24};

    int pt_to_z2[N];
    get_mapping(o1, o2, pt_to_z2);

    int pt[N];
    for (int t = 0; t < N; t++) {
        int pos = pt_to_z2[t];
        int sh = shifts[pos % 28];
        int c_val = ct_kr[pos];
        int p_val = (sh - c_val + 26) % 26;
        pt[t] = kr_to_std[p_val];
    }

    float sc = score_quadgrams(pt);
    printf("Score with exact 28 shifts: %.4f\n", sc);
    char buf[N+1];
    for (int i = 0; i < N; i++) buf[i] = pt[i] + 'A';
    buf[N] = 0;
    printf("Plaintext: %s\n", buf);

    // Now test with pure base_q4 and base_q7:
    int q4[4] = {0, 9, 13, 2};
    int q7[7] = {21, 18, 19, 19, 16, 0, 3};
    for (int t = 0; t < N; t++) {
        int pos = pt_to_z2[t];
        int sh = (q4[pos % 4] + q7[pos % 7]) % 26;
        int c_val = ct_kr[pos];
        int p_val = (sh - c_val + 26) % 26;
        pt[t] = kr_to_std[p_val];
    }
    float sc_pure = score_quadgrams(pt);
    printf("Score with pure (q4, q7): %.4f\n", sc_pure);
    for (int i = 0; i < N; i++) buf[i] = pt[i] + 'A';
    buf[N] = 0;
    printf("Plaintext: %s\n", buf);

    return 0;
}

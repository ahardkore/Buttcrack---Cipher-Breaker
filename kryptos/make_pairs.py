pairs = [
    ("NEEDLEMAKING", "GOLDSMITHING"),
    ("GOLDSMITHING", "NEEDLEMAKING"),
    ("NEEDLEMAKING", "METALWORKING"),
    ("METALWORKING", "NEEDLEMAKING"),
    ("NEEDLEMAKING", "PATTERNMAKER"),
    ("PATTERNMAKER", "NEEDLEMAKING"),
    ("NEEDLEMAKING", "BELLOWSMAKER"),
    ("BELLOWSMAKER", "NEEDLEMAKING"),
    ("NEEDLEMAKING", "THIMBLEMAKER"),
    ("THIMBLEMAKER", "NEEDLEMAKING"),
    ("NEEDLEMAKING", "SILVERWORKER"),
    ("SILVERWORKER", "NEEDLEMAKING"),
    ("NEEDLEMAKING", "SILVERBEATER"),
    ("SILVERBEATER", "NEEDLEMAKING"),
    ("NEEDLEMAKING", "GROUNDNEEDLE"),
    ("GROUNDNEEDLE", "NEEDLEMAKING"),
    ("NEEDLEMAKING", "ELECTROPLATE"),
    ("ELECTROPLATE", "NEEDLEMAKING"),
    ("NEEDLEMAKING", "COUNTERPUNCH"),
    ("COUNTERPUNCH", "NEEDLEMAKING"),
    ("NEEDLEMAKING", "LOCKSMITHING"),
    ("LOCKSMITHING", "NEEDLEMAKING"),
    ("GOLDSMITHING", "METALWORKING"),
    ("METALWORKING", "GOLDSMITHING"),
    ("GOLDSMITHING", "PATTERNMAKER"),
    ("PATTERNMAKER", "GOLDSMITHING"),
    ("GOLDSMITHING", "BELLOWSMAKER"),
    ("BELLOWSMAKER", "GOLDSMITHING"),
    ("GOLDSMITHING", "SILVERWORKER"),
    ("SILVERWORKER", "GOLDSMITHING"),
    ("GOLDSMITHING", "SILVERBEATER"),
    ("SILVERBEATER", "GOLDSMITHING"),
]

with open("test_pairs.c", "w") as f:
    f.write(r"""#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int ct_std[N];
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
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
}

void keyword_to_order(const char *kw, int *order, int len) {
    int used[32] = {0}, count = 0;
    for (int c = 'A'; c <= 'Z'; c++) {
        for (int i = 0; i < len; i++) {
            if (kw[i] == c && !used[i]) { order[count++] = i; used[i] = 1; }
        }
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

float score_quadgrams(const int *txt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) s += quad_table[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    return s / (N - 3);
}

typedef struct { const char *w1; const char *w2; } Pair;
""")

    f.write(f"static const Pair PAIRS[] = {{\n")
    for w1, w2 in pairs:
        f.write(f'    {{"{w1}", "{w2}"}},\n')
    f.write(f"}};\n")
    f.write(f"static const int NUM_PAIRS = {len(pairs)};\n")

    f.write(r"""
int main() {
    load_models();
    for (int i = 0; i < NUM_PAIRS; i++) {
        const char *w1 = PAIRS[i].w1;
        const char *w2 = PAIRS[i].w2;
        int order1[W], order2[W];
        keyword_to_order(w1, order1, W);
        keyword_to_order(w2, order2, W);

        int identity[N]; for (int j = 0; j < N; j++) identity[j] = j;
        int after2[N], pt_to_z2[N];
        col_decrypt(identity, order2, after2, W, H);
        col_decrypt(after2, order1, pt_to_z2, W, H);

        for (int mode = 0; mode < 4; mode++) {
            int use_kr = (mode == 0 || mode == 1);
            int is_beau = (mode == 1 || mode == 3);
            const int *src_ct = use_kr ? ct_kr : ct_std;
            const int *to_std = use_kr ? kr_to_std : NULL;

            int best_shifts[28];
            for (int s = 0; s < 28; s++) {
                double best_s_sc = -1e9; int best_sh = 0;
                for (int sh = 0; sh < 26; sh++) {
                    double cur_s_sc = 0.0;
                    for (int t = 0; t < N; t++) {
                        int pos = pt_to_z2[t];
                        if (pos % 28 == s) {
                            int c_val = src_ct[pos];
                            int p_val = is_beau ? (sh - c_val + 26) % 26 : (c_val - sh + 26) % 26;
                            int std_c = use_kr ? to_std[p_val] : p_val;
                            cur_s_sc += log_monogram[std_c];
                        }
                    }
                    if (cur_s_sc > best_s_sc) { best_s_sc = cur_s_sc; best_sh = sh; }
                }
                best_shifts[s] = best_sh;
            }

            int pt[N];
            for (int t = 0; t < N; t++) {
                int pos = pt_to_z2[t];
                int sh = best_shifts[pos % 28];
                int c_val = src_ct[pos];
                int p_val = is_beau ? (sh - c_val + 26) % 26 : (c_val - sh + 26) % 26;
                pt[t] = use_kr ? to_std[p_val] : p_val;
            }
            float sc = score_quadgrams(pt);
            if (sc > -6.5) {
                char pt_str[N+1];
                for (int j = 0; j < N; j++) pt_str[j] = pt[j] + 'A';
                pt_str[N] = '\0';
                printf("Score: %.4f | (%s, %s) Mode %d\n  PT: %.80s\n", sc, w1, w2, mode, pt_str);
            }
        }
    }
    return 0;
}
""")

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

#define N 144
float quad_table[26*26*26*26];
int alph_to_std[26];

int get_idx(char c) {
    for (int i = 0; i < 26; i++) {
        if (ALPH[i] == c) return i;
    }
    return -1;
}

void load_quads() {
    for (int i = 0; i < 26*26*26*26; i++) quad_table[i] = -8.0f;
    for (int i = 0; i < 26; i++) alph_to_std[i] = ALPH[i] - 'A';

    FILE *f = fopen("/home/user/english_quads.tsv", "r");
    if (!f) exit(1);
    char line[128];
    while (fgets(line, sizeof(line), f)) {
        char q[5];
        float sc;
        if (sscanf(line, "%4s\t%f", q, &sc) == 2) {
            int c0 = q[0] - 'A', c1 = q[1] - 'A', c2 = q[2] - 'A', c3 = q[3] - 'A';
            if (c0>=0 && c0<26 && c1>=0 && c1<26 && c2>=0 && c2<26 && c3>=0 && c3<26) {
                int code = ((c0 * 26 + c1) * 26 + c2) * 26 + c3;
                quad_table[code] = sc;
            }
        }
    }
    fclose(f);
}

// Global storage for permutations
int perms_6[720][6]; int n_p6 = 0;
int perms_8[25000][8]; int n_p8 = 0;
int perms_9[45000][9]; int n_p9 = 0;
int perms_12[30000][12]; int n_p12 = 0;
int perms_16[6000][16]; int n_p16 = 0;

void load_perms() {
    FILE *f = fopen("/home/user/words_alpha.txt", "r");
    if (!f) exit(1);
    char line[128];
    while (fgets(line, sizeof(line), f)) {
        int L = strlen(line);
        while (L > 0 && (line[L-1] == '\r' || line[L-1] == '\n')) line[--L] = '\0';
        if (L == 6) {
            // compute perm
            int p[6];
            for (int i=0; i<6; i++) {
                int r = 0;
                for (int j=0; j<6; j++) {
                    if (line[j] < line[i] || (line[j] == line[i] && j < i)) r++;
                }
                p[i] = r;
            }
            // check if exists
            int seen = 0;
            for (int k=0; k<n_p6; k++) {
                if (memcmp(perms_6[k], p, 6*sizeof(int)) == 0) { seen = 1; break; }
            }
            if (!seen && n_p6 < 720) {
                memcpy(perms_6[n_p6++], p, 6*sizeof(int));
            }
        } else if (L == 8) {
            int p[8];
            for (int i=0; i<8; i++) {
                int r = 0;
                for (int j=0; j<8; j++) {
                    if (line[j] < line[i] || (line[j] == line[i] && j < i)) r++;
                }
                p[i] = r;
            }
            int seen = 0;
            for (int k=0; k<n_p8; k++) {
                if (memcmp(perms_8[k], p, 8*sizeof(int)) == 0) { seen = 1; break; }
            }
            if (!seen && n_p8 < 25000) {
                memcpy(perms_8[n_p8++], p, 8*sizeof(int));
            }
        }
    }
    fclose(f);
    printf("Loaded perms: w6=%d, w8=%d\n", n_p6, n_p8);
}

int main() {
    load_quads();
    load_perms();

    int c_arr[N];
    for (int i = 0; i < N; i++) c_arr[i] = get_idx(CT[i]);

    const char *keys[] = {
        "WEBSTER", "WOMACKA", "WILLIAM", "WALTERW", "LANGLEY", "BERLINS",
        "KRYPTOS", "SANBORN", "SCHEIDT", "PALIMPS", "PROVENA", "MARGINS",
        "ORDINAT", "PORTALS", "NEEDLES", "WHITESM", "FORGING", "HEARTHS",
        NULL
    };

    float global_best_sc = -999.0f;
    char global_best_pt[N+1];

    for (int k_idx = 0; keys[k_idx]; k_idx++) {
        const char *key = keys[k_idx];
        int shifts[7];
        for (int i = 0; i < 7; i++) shifts[i] = get_idx(key[i]);

        int M[N];
        for (int i = 0; i < N; i++) {
            M[i] = (c_arr[i] - shifts[i % 7] + 26) % 26;
        }

        // Test width 8
        int rows = 18;
        for (int p_idx = 0; p_idx < n_p8; p_idx++) {
            int *perm = perms_8[p_idx];
            int pt_std[N];
            for (int r = 0; r < rows; r++) {
                for (int c_idx = 0; c_idx < 8; c_idx++) {
                    int orig_col = perm[c_idx];
                    int m_idx = c_idx * rows + r;
                    pt_std[r * 8 + orig_col] = alph_to_std[M[m_idx]];
                }
            }

            float sc = 0.0f;
            for (int i = 0; i < N - 3; i++) {
                int code = ((pt_std[i] * 26 + pt_std[i+1]) * 26 + pt_std[i+2]) * 26 + pt_std[i+3];
                sc += quad_table[code];
            }
            sc /= (N - 3);

            if (sc > global_best_sc) {
                global_best_sc = sc;
                for (int i = 0; i < N; i++) {
                    for (int j = 0; j < 26; j++) {
                        if (alph_to_std[j] == pt_std[i]) { global_best_pt[i] = ALPH[j]; break; }
                    }
                }
                global_best_pt[N] = '\0';
                if (sc > -5.5f) {
                    printf("HIT: key=%s w=8 score=%.3f | PT: %s\n", key, sc, global_best_pt);
                }
            }
        }
    }

    printf("Tested all WW keys on W=8. Best score: %.3f\n", global_best_sc);
    printf("PT: %s\n", global_best_pt);
    return 0;
}

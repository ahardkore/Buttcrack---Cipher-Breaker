#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N 153

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const int ps[4] = {4, 5, 6, 7};
static int c_idx[N];
static int char_to_k[256];

void get_row(int pos, int *row) {
    memset(row, 0, 22 * sizeof(int));
    row[pos % 4] = 1;
    row[4 + (pos % 5)] = 1;
    row[9 + (pos % 6)] = 1;
    row[15 + (pos % 7)] = 1;
}

// Simple Gaussian elimination over GF(P)
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

    if (pivot == -1) {
        return val == 0;
    }

    int inv = inv_mod(row[pivot], s->p);
    for (int j = 0; j < 22; j++) {
        s->basis[pivot][j] = (row[j] * inv) % s->p;
    }
    s->rhs[pivot] = (val * inv) % s->p;
    s->has_pivot[pivot] = 1;
    return 1;
}

int main() {
    for (int i = 0; i < 256; i++) char_to_k[i] = -1;
    for (int i = 0; i < 26; i++) {
        char_to_k[(unsigned char)KRYPTOS[i]] = i;
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = char_to_k[(unsigned char)PK8_CT[i]];
    }

    const char *base = "ATLASTTHEFIREWAS";
    int base_len = strlen(base);

    Sys base2, base13;
    init_sys(&base2, 2);
    init_sys(&base13, 13);

    for (int i = 0; i < base_len; i++) {
        int r[22];
        get_row(i, r);
        int rhs = (c_idx[i] - char_to_k[(unsigned char)base[i]] + 26) % 26;
        add_eq(&base2, r, rhs);
        add_eq(&base13, r, rhs);
    }

    printf("Base set: %s (len %d)\n", base, base_len);

    // Read words from words_5.txt, words_6.txt, words_7.txt
    FILE *f = fopen("words_5.txt", "r");
    if (!f) return 1;

    char word[64];
    int count = 0;
    while (fscanf(f, "%s", word) == 1) {
        int wlen = strlen(word);
        if (wlen < 3) continue;

        Sys s2 = base2;
        Sys s13 = base13;
        int ok = 1;

        for (int j = 0; j < wlen; j++) {
            int pos = base_len + j;
            int r[22];
            get_row(pos, r);
            int rhs = (c_idx[pos] - char_to_k[(unsigned char)word[j]] + 26) % 26;
            if (!add_eq(&s2, r, rhs) || !add_eq(&s13, r, rhs)) {
                ok = 0;
                break;
            }
        }

        if (ok) {
            printf("CONSISTENT: %s%s (word: %s)\n", base, word, word);
            count++;
        }
    }
    fclose(f);
    printf("Total consistent 5-letter words found: %d\n", count);
    return 0;
}

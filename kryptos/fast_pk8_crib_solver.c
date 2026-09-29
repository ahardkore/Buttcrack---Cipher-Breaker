#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static const char *pk8_raw = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";
static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int kr_to_num[26];
static int num_to_kr[26];
static int ct8[153];
static float quad[26][26][26][26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        kr_to_num[KRYPTOS[i] - 'A'] = i;
        num_to_kr[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < 153; i++) {
        ct8[i] = kr_to_num[pk8_raw[i] - 'A'];
    }

    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) return;
    char buf[64];
    double total = 0;
    while (fgets(buf, sizeof(buf), f)) {
        char qg[8]; double cnt;
        if (sscanf(buf, "%s %lf", qg, &cnt) == 2) total += cnt;
    }
    rewind(f);
    while (fgets(buf, sizeof(buf), f)) {
        char qg[8]; double cnt;
        if (sscanf(buf, "%s %lf", qg, &cnt) == 2 && strlen(qg) == 4) {
            quad[qg[0]-'A'][qg[1]-'A'][qg[2]-'A'][qg[3]-'A'] = (float)log10(cnt / total);
        }
    }
    fclose(f);
}

// Invert modulo 2
static int inv2(int a) { return (a % 2 != 0) ? 1 : 0; }
// Invert modulo 13
static int inv13(int a) {
    a = (a % 13 + 13) % 13;
    for (int x = 1; x < 13; x++) if ((a * x) % 13 == 1) return x;
    return 0;
}

// Solve linear system A x = b over Z26 by CRT (Z2 and Z13)
// 18 variables: q4[1..3] (3), q5[0..4] (5), q6[0..4] (5) [since q6[5]=-sum], q7[0..5] (5) [since q7[6]=-sum]
// Total variables: 4 + 5 + 6 + 7 = 22, with 4 gauge constraints:
// Let q4[0]=0, q5[0]=0, q6[0]=0, q7[0..6] free.
// Variables:
// 0..2: q4[1], q4[2], q4[3]  (q4[0] = 0)
// 3..6: q5[1], q5[2], q5[3], q5[4] (q5[0] = 0)
// 7..11: q6[1]..q6[5] (q6[0] = 0)
// 12..18: q7[0]..q7[6] (all 7 free, includes global offset)
// Total variables: 3 + 4 + 5 + 7 = 19 variables.
// Wait! lcm(4,5,6,7) = 420.
// gcd(4,6) = 2, so q4 and q6 share a Z2 component!
// Thus effective dimension over Z26 is:
// over Z13: 4 + 5 + 6 + 7 - 3 = 19?
// Let's check rank: 18 equations of full rank determine all 153 key positions!


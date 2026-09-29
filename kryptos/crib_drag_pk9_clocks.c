#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int c_idx[N];
static int char_to_k[256];

void init_tables() {
    for (int i = 0; i < 256; i++) char_to_k[i] = -1;
    for (int i = 0; i < 26; i++) {
        char_to_k[(unsigned char)KRYPTOS[i]] = i;
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = char_to_k[(unsigned char)PK9_CT[i]];
    }
}

// Check if a sequence of keystream values k[0..len-1] at offset 'start'
// is consistent with k[i] = (Q4[i % 4] + Q7[i % 7]) % 26
int is_consistent_q4_q7(const int *k_vals, int len, int start) {
    // We solve for Q4[0..3] and Q7[0..6] in Z26
    // Fix gauge Q4[0] = 0
    // Try all 26^3 values of Q4[1..3]
    for (int q4_1 = 0; q4_1 < 26; q4_1++) {
        for (int q4_2 = 0; q4_2 < 26; q4_2++) {
            for (int q4_3 = 0; q4_3 < 26; q4_3++) {
                int q4[4] = {0, q4_1, q4_2, q4_3};
                int q7[7];
                int q7_set[7] = {0};
                int ok = 1;

                for (int idx = 0; idx < len; idx++) {
                    int pos = start + idx;
                    int r7 = pos % 7;
                    int r4 = pos % 4;
                    int req_q7 = (k_vals[idx] - q4[r4] + 26) % 26;

                    if (q7_set[r7]) {
                        if (q7[r7] != req_q7) {
                            ok = 0;
                            break;
                        }
                    } else {
                        q7_set[r7] = 1;
                        q7[r7] = req_q7;
                    }
                }

                if (ok) return 1; // Found consistent Q4 and Q7
            }
        }
    }
    return 0;
}

void test_crib(const char *crib_text) {
    // Clean crib text (uppercase alpha only)
    char crib[256];
    int len = 0;
    for (int i = 0; crib_text[i]; i++) {
        char c = crib_text[i];
        if (c >= 'a' && c <= 'z') c -= 32;
        if (c >= 'A' && c <= 'Z') crib[len++] = c;
    }
    crib[len] = '\0';
    if (len < 14) return;

    int k_vals[256];

    // Drag across all positions in PK9
    for (int start = 0; start <= N - len; start++) {
        // Vigenere: p = (c - k) % 26 => k = (c - p) % 26
        for (int idx = 0; idx < len; idx++) {
            int c = c_idx[start + idx];
            int p = char_to_k[(unsigned char)crib[idx]];
            k_vals[idx] = (c - p + 26) % 26;
        }

        if (is_consistent_q4_q7(k_vals, len, start)) {
            printf(">>> CONSISTENT CRIB HIT (Vigenere) at pos %d: '%s'\n", start, crib);
        }

        // Beaufort: p = (k - c) % 26 => k = (p + c) % 26
        for (int idx = 0; idx < len; idx++) {
            int c = c_idx[start + idx];
            int p = char_to_k[(unsigned char)crib[idx]];
            k_vals[idx] = (p + c) % 26;
        }

        if (is_consistent_q4_q7(k_vals, len, start)) {
            printf(">>> CONSISTENT CRIB HIT (Beaufort) at pos %d: '%s'\n", start, crib);
        }
    }
}

int main() {
    init_tables();
    printf("Testing Thematic Cribs against PK9 (Q4 + Q7 model)...\n");

    const char *cribs[] = {
        "THEWHITESMITH",
        "WHITESMITHSWORKSHOP",
        "WORKSHOPOFHISTRADE",
        "OLDTOOLSOFHISTRADE",
        "STUDYUNDERHIM",
        "FORTENYEARSHEWILL",
        "LETMEONECLAIM",
        "TAKEOFMEYOUROWNMAKING",
        "ANEEDLESOSLENDER",
        "TOREADANYKNOT",
        "READANYKNOT",
        "PELLEGRIN",
        "VIENNESEANATOMIST",
        "ANATOMISTINBERN",
        "SLOWLYDESPARATLY",
        "REMAINSOFPASSAGE",
        "PASSAGEDEBRIS",
        "WHOKNOWSTHEEXACT",
        "ONLYWW",
        "ITWASDELIBERATELY",
        "DELIBERATELYBURIED",
        "CANSEEPARADOX",
        "EASTNORTHEAST",
        "NORTHEAST",
        "BETWEENSUBTLE",
        "SHADINGANDTHE",
        "ABSENCEOFLIGHT",
        "LIESANILLUSION",
        "LAYERSOFRUST",
        "TEMPERTHESTEEL",
        "HAMMERANDANVIL",
        "HEATOFTHEFORGE",
        "BELLOWSANDFIRE",
        "DRAWNTHROUGHIRON",
        "COPPERANDBRASS",
        "SILVERANDGOLD",
        "CRUCIBLEANDTONGS",
        "CASTINTOBRONZE",
        "POLISHEDWITHCLAY",
        "SECRETSOFTHECRAFT",
        "TRANSMUTATION",
        "PHILOSOPHER",
        "ALCHEMIST",
        "SEVENMETALS",
        "PLANETARYHOURS",
        "ASTROLOGICAL",
        "FOURCLOCKS",
        "TWELVECOLUMNS",
        "FOURTEENROUNDS",
        "TWENTYFOURHOURS",
        "FORTYDIVISIONS",
        NULL
    };

    for (int i = 0; cribs[i]; i++) {
        test_crib(cribs[i]);
    }

    printf("Crib testing completed.\n");
    return 0;
}

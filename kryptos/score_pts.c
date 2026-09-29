#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) return;
    char q[16]; float cnt;
    double total = 0;
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    rewind(f);
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);
}

float score_txt(const char *t) {
    int n = strlen(t);
    float sc = 0.0f;
    for (int i=0; i<n-3; i++) {
        sc += quad[t[i]-'A'][t[i+1]-'A'][t[i+2]-'A'][t[i+3]-'A'];
    }
    return sc / (n - 3);
}

int main() {
    load_quads();
    const char *w12 = "HIERHIOTRUAIDHRMNSHOLTCSLSWOSAOMENOWENUTAUORNMNDRSHILINSFSNONSESNFWITARSCAHEADEAMOHCOCTGONENDFITPSTEEEDERWEFDIRLIFHENSEASSATOFINOULIOFHASOUSSEDH";
    const char *w16 = "EDCUORATHAMEARSULSTINSCIDODRCAUTDOFFWIOSLERWSHENHIADEANEEINUIRIMNHINENNGROOHSLSSSSHEDERENSSEFEWAANRFHEHLCITHONDOLSMFINITOSOTHFOFNSOOUSEAPAMTOTSW";
    printf("Width 12 Quad: %.3f\n", score_txt(w12));
    printf("Width 16 Quad: %.3f\n", score_txt(w16));
    return 0;
}

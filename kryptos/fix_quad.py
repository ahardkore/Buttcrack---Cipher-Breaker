with open("test_pk9_decoupled_double_col.c") as f:
    code = f.read()

old_load = """void load_quadgrams() {
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    qgram[i][j][k][l] = -15.0f;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
    if (!f) {
        printf("Error: quadgrams file not found\\n");
        exit(1);
    }
    char line[64];
    while (fgets(line, sizeof(line), f)) {
        char g[5];
        float val;
        if (sscanf(line, "%4s %f", g, &val) == 2) {
            int a = g[0] - 'A';
            int b = g[1] - 'A';
            int c = g[2] - 'A';
            int d = g[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                qgram[a][b][c][d] = val;
            }
        }
    }
    fclose(f);
}"""

new_load = """void load_quadgrams() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    qgram[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
    if (!f) {
        printf("Error: quadgrams file not found\\n");
        exit(1);
    }
    char line[64];
    double total = 5348433.0;
    while (fgets(line, sizeof(line), f)) {
        char g[5];
        double count;
        if (sscanf(line, "%4s %lf", g, &count) == 2) {
            int a = g[0] - 'A';
            int b = g[1] - 'A';
            int c = g[2] - 'A';
            int d = g[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                qgram[a][b][c][d] = (float)log10(count / total);
            }
        }
    }
    fclose(f);
}"""

assert old_load in code
code = code.replace(old_load, new_load)
with open("test_pk9_decoupled_double_col.c", "w") as f:
    f.write(code)
print("Updated quadgram loader!")

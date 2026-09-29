with open("all_words.txt") as f:
    words = [w.strip().upper() for w in f if 3 <= len(w.strip()) <= 8 and w.strip().isalpha()]

# Take top 5000 common words
common = words[:5000]

with open("common_words.h", "w") as f:
    f.write("// Compact common words list for scoring\n")
    f.write(f"#define N_COMMON_WORDS {len(common)}\n")
    f.write("static const char *common_words[N_COMMON_WORDS] = {\n")
    for w in common:
        f.write(f'    "{w}",\n')
    f.write("};\n")

print(f"Generated common_words.h with {len(common)} words.")

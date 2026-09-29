import math

with open("english_quads.tsv") as f:
    quad = {line.split('\t')[0]: float(line.split('\t')[1]) for line in f}

floor = -9.5
def score_quad(text):
    return sum(quad.get(text[i:i+4], floor) for i in range(len(text)-3)) / (len(text)-3)

rows = [
    "JVRMBLARDADEFUNCTO",
    "RDQBOOMRBETHSKWJER",
    "SOISEARVEMYLAILEBO",
    "THEEDAMESQUNGLAYIM",
    "ELIFORESSESTIAAUON",
    "EASTYMARINPRAYIALM",
    "IRLOFATSEREDCISANT",
    "IDBYOUSCHESALSOMYR"
]

print("Baseline (Left-to-Right by rows):", score_quad("".join(rows)))

# Route 1: Boustrophedon (even L->R, odd R->L)
boust = []
for r, row in enumerate(rows):
    if r % 2 == 1:
        boust.append(row[::-1])
    else:
        boust.append(row)
boust_pt = "".join(boust)
print(f"Boustrophedon (even L->R, odd R->L): {score_quad(boust_pt):.4f}")

# Route 2: Boustrophedon (odd L->R, even R->L)
boust2 = []
for r, row in enumerate(rows):
    if r % 2 == 0:
        boust2.append(row[::-1])
    else:
        boust2.append(row)
boust2_pt = "".join(boust2)
print(f"Boustrophedon (odd L->R, even R->L): {score_quad(boust2_pt):.4f}")

# Route 3: Read by columns (top-to-bottom)
col_read = "".join(rows[r][c] for c in range(18) for r in range(8))
print(f"Read by columns: {score_quad(col_read):.4f}")

# Route 4: Reverse overall text
print(f"Full reverse: {score_quad(''.join(rows)[::-1]):.4f}")

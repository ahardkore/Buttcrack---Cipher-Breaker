import re

with open('all_words.txt') as f:
    dict_words = set(w.strip().upper() for w in f)

with open('theophilus_book3_english.txt') as f:
    text1 = f.read().upper()

with open('theophilus_hendrie.txt') as f:
    text2 = f.read().upper()

corpus_words = set(re.findall(r'[A-Z]+', text1 + ' ' + text2))
english_craft_words = corpus_words.intersection(dict_words)

w4 = sorted([w for w in english_craft_words if len(w) == 4])
w5 = sorted([w for w in english_craft_words if len(w) == 5])
w6 = sorted([w for w in english_craft_words if len(w) == 6])
w7 = sorted([w for w in english_craft_words if len(w) == 7])

print(f"W4={len(w4)}, W5={len(w5)}, W6={len(w6)}, W7={len(w7)}")

with open("theophilus_w4.txt", "w") as f:
    for w in w4: f.write(w + "\n")
with open("theophilus_w5.txt", "w") as f:
    for w in w5: f.write(w + "\n")
with open("theophilus_w6.txt", "w") as f:
    for w in w6: f.write(w + "\n")
with open("theophilus_w7.txt", "w") as f:
    for w in w7: f.write(w + "\n")

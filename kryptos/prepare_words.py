with open('/home/user/words_alpha.txt') as f:
    words = [line.strip().upper() for line in f if line.strip().isalpha()]

by_len = {}
for w in words:
    L = len(w)
    if L not in by_len: by_len[L] = []
    by_len[L].append(w)

for L in [3, 4, 5, 6, 7, 8]:
    w_list = sorted(list(set(by_len.get(L, []))))
    with open(f'/home/user/words_{L}.txt', 'w') as out:
        for w in w_list:
            out.write(w + '\n')
    print(f'Length {L}: {len(w_list)} words saved to words_{L}.txt')

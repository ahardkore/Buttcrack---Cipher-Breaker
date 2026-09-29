shifts = [5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3]

# Test which clock combination best fits the 28 shifts:
# Possible periods that divide 420 or 28:
# Clocks {4, 7}:
# Can we fit shifts[i] = a[i % 4] + b[i % 7] (mod 26)?
# Let us use integer linear programming / brute force over 26^3 for a:
best_matches = 0
best_a, best_b = None, None
for a1 in range(26):
    for a2 in range(26):
        for a3 in range(26):
            a = [0, a1, a2, a3]
            m = 0
            cur_b = []
            for j in range(7):
                # shifts[j + 7k] - a[(j + 7k)%4]
                vals = [(shifts[j + 7*k] - a[(j + 7*k) % 4]) % 26 for k in range(4)]
                from collections import Counter
                val, count = Counter(vals).most_common(1)[0]
                m += count
                cur_b.append(val)
            if m > best_matches:
                best_matches = m
                best_a = list(a)
                best_b = list(cur_b)

print(f"Clock {{4, 7}} exact matches: {best_matches}/28")
print(f"  a: {best_a}")
print(f"  b: {best_b}")

# What about Clock {2, 14}?
# shifts[i] = a[i % 2] + b[i % 14]
best_m14 = 0
for a1 in range(26):
    a = [0, a1]
    m = 0
    for j in range(14):
        vals = [(shifts[j + 14*k] - a[(j + 14*k) % 2]) % 26 for k in range(2)]
        if vals[0] == vals[1]: m += 2
        else: m += 1
    if m > best_m14:
        best_m14 = m
print(f"Clock {{2, 14}} exact matches: {best_m14}/28")

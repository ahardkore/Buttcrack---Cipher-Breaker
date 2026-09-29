shifts = [5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3]

# Test LCG: s_{n+1} = a * s_n + c (mod M) for M in [26, 27, 28, 31, 32]
for M in [26, 28, 32]:
    for a in range(M):
        for c in range(M):
            matches = sum(1 for i in range(27) if (a * shifts[i] + c) % M == shifts[i+1])
            if matches > 10:
                print(f"LCG mod {M}: a={a}, c={c} => {matches}/27 matches")

# Test Fibonacci-like: s_{n} = a * s_{n-1} + b * s_{n-2} (mod M)
for M in [26, 28]:
    for a in range(M):
        for b in range(M):
            matches = sum(1 for i in range(2, 28) if (a * shifts[i-1] + b * shifts[i-2]) % M == shifts[i])
            if matches > 10:
                print(f"Fib mod {M}: a={a}, b={b} => {matches}/26 matches")

with open('attack_pk9_held_karp.c') as f:
    code = f.read()

# Make dp and parent non-static local arrays
code = code.replace('static float dp[4096][W];\n    static int parent[4096][W];',
                    'float dp[4096][W];\n    int parent[4096][W];')

# Change threshold from 760 to 720
code = code.replace('if (sc > 760.0)', 'if (sc > 720.0)')

# Print whenever any candidate is evaluated or print best
code = code.replace('if (qsc > -6.5f)', 'if (qsc > -8.5f)')

with open('attack_pk9_held_karp.c', 'w') as f:
    f.write(code)

print("Fixed thread safety and thresholds.")

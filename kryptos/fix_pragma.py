with open("test_crib_pk8_fast.c") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "max_sc_seen" in line and "pragma" in line:
        new_lines.append("""
        if (avg_sc > max_sc_seen) {
            #pragma omp critical
            {
                if (avg_sc > max_sc_seen) max_sc_seen = avg_sc;
            }
        }
""")
    else:
        new_lines.append(line)

with open("test_crib_pk8_fast.c", "w") as f:
    f.writelines(new_lines)

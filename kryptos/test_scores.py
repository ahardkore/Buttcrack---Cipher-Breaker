with open("test_crib_pk8_fast.c") as f:
    code = f.read()

# Let's track global_max_sc and print it at the end
old = """    double t1 = omp_get_wtime();
    printf("Completed all %d cribs in %.2f seconds!\\n", num_cribs, t1 - t0);"""

new = """    printf("\\nMax score observed across all cribs: %.4f\\n", max_sc_seen);
    double t1 = omp_get_wtime();
    printf("Completed all %d cribs in %.2f seconds!\\n", num_cribs, t1 - t0);"""

code = "static float max_sc_seen = -999.0f;\n" + code
code = code.replace("float avg_sc = sc / (N - 3);", "float avg_sc = sc / (N - 3);\nif (avg_sc > max_sc_seen) { #pragma omp critical { if (avg_sc > max_sc_seen) max_sc_seen = avg_sc; } }")
code = code.replace(old, new)

with open("test_crib_pk8_fast.c", "w") as f:
    f.write(code)


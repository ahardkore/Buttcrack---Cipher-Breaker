import re

with open("sa_pk9_double_col.c") as f:
    code = f.read()

# Only test mode 1 and mode 3
code = code.replace("for (int mode = 0; mode < 4; mode++) {", 
                    "for (int mode_idx = 0; mode_idx < 2; mode_idx++) { int mode = (mode_idx == 0) ? 1 : 3;")

# Set restarts to 100 and steps to 1500
code = re.sub(r'restart < \d+', 'restart < 80', code)
code = re.sub(r'step < \d+', 'step < 1200', code)

with open("sa_pk9_double_col_deep.c", "w") as f:
    f.write(code)


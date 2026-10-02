from z3 import *

# Create 8 symbolic variables (one byte for each of the 8 characters)
chars = [BitVec(f'c_{i}', 32) for i in range(8)]

# Initialize hash
h = BitVecVal(0, 32)

# Run the loop exactly like in the C code
for c in chars:
    	h = c + h * 31

# Create the solver
s = Solver()

# Add condition: the final hash must equal our target value
s.add(h == 1741233685)

# Constrain characters to printable ASCII symbols (from 32 to 126)
for c in chars:
    	s.add(c >= 32, c <= 126)

# Run the search
if s.check() == sat:
    	model = s.model()
    	# Reassemble the found string
    	result_chars = []
    	for i in range(8):
    	    val = model[chars[i]].as_long()
    	    result_chars.append(chr(val))
    	print("Found first part of the key:", "".join(result_chars))
else:
    	print("No solution found (check target hash or character range).")

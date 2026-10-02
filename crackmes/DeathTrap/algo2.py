from z3 import *

# Create 8 symbolic variables (one for each of the 8 bytes of the second block)
chars = [BitVec(f'b_{i}', 32) for i in range(8)]

# Initial value of uVar1 (from previous assembly analysis: 0xDEADBEEF)
uVar1 = 3735928559 
DELTA = 2654435769  # 0x9e3779b9

# Recreate the loop from the decompiled code
for c in chars:
    	# Equivalent to: uVar1 = ((*ptr_to_buffer8 ^ uVar1) << 5 | uVar1 >> 0x1b) + 2654435769;
    	xor_val = c ^ uVar1
    	# Circular left shift by 5: (xor_val << 5) | (LShR(xor_val, 27))
    	rolled = (xor_val << 5) | LShR(xor_val, 27)
    	uVar1 = (rolled + DELTA)
    
    	# uVar1 = uVar1 >> 0x10 ^ uVar1;
    	uVar1 = LShR(uVar1, 16) ^ uVar1

# Create the Z3 solver
s = Solver()

# Target value that uVar1 must reach
s.add(uVar1 == 0xc5b6c81)

# Constrain the characters to printable ASCII range (from ' ' (32) to '~' (126))
for c in chars:
    	s.add(c >= 32, c <= 126)

# Run the search
if s.check() == sat:
    	model = s.model()
    	result_chars = []
    	for i in range(8):
        	val = model[chars[i]].as_long()
        	result_chars.append(chr(val))
    	print("Found second part of the key:", "".join(result_chars))
else:
    	print("No solution found. Check initial value of uVar1 or character range.")

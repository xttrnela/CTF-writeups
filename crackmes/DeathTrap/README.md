### [soulreaper](https://crackmes.one/user/soulreaper)'s Death Trap
Web Platform: crackmes.one
Language: C/C++
Platform: Unix/Linux
Difficulty: 2.8
Personal Rating: ~2.5
Reverse Engineering task performed on a VirtualBox Debian 13 VM.

## Task Overview
The purpose of this crackme is to  find the correct  serial  key.

Unpacking the archive using the standard crackmes.one password. This is an x86-64 ELF file. We will immediately make it executable using the command `chmod u+x sysupdate.`

>   xela@pcdeblin:~/crackme/pwn$ chmod u+x vuln

Next, we use Ghidra to view the decompiled code.
This  code  demonstrates  interprocess  communication  (IPC)  in  UNIX/Linux  operating  systems  using an anonymous  pipe  and  process  separation  via the fork()  system  call. After  the  current  (source)  process has requested  serial,  it  creates a child  process  in  which it reads the entered  50  bytes  into the buffer.  since  serial  initially  holds  64  bytes,  and the buffer  is  8  bytes in size, the remaining  42  bytes of our  serial  overflow the buffer  and are written  further  in  stack  memory to the local_40 array,  which is 48  bytes in size. Next, the program works with the first 16 bytes of our serial, where the first 8 bytes are hashed in the child process of our original parent, and the other 8 bytes are hashed in the descendant of our child process. 
The source and child processes check the execution status of their child processes. if serial is entered correctly, we will be able to pass the condition.
To solve this problem, I wrote two scripts in Python, where based on the hashing algorithm, the first script outputs the first 8 bytes of serial, and the second script outputs the next 8 bytes, respectively.

The hashing  algorithms  look like this  in  the  decompiler:
*First algorithm

 

    do {
            symbol = *bufptr;
            bufptr = bufptr + 1;
            hash = (uint)symbol + hash * 31;
      } while (bufptr != &local_a6);

  


*Second Algorithm
 

     lVar4 = 0;
     uVar1 = 3735928559;
     do {
		     ptr_to_buffer8 = (byte *)(pcVar3 + lVar4);
		     lVar4 = lVar4 + 1;
		     uVar1 = ((*ptr_to_buffer8 ^ uVar1) << 5 | uVar1 >> 0x1b) + 2654435769;
		     uVar1 = uVar1 >> 0x10 ^ uVar1;
     } while (lVar4 != 8);

For  scripts, we  will  use the z3-solver  library,  which  uses the Z3  Theorem  Prover  to  find  input  data using a  known  hash  or  mathematical  formula.

algo.py for first 8 bytes.

    from z3 import *
    
    #Create 8 symbolic variables (one byte for each of the 8 characters)
    chars = [BitVec(f'c_{i}', 32) for i in range(8)]
    
    #Initialize hash
    h = BitVecVal(0, 32)
    
    #Run the loop exactly like in the C code
    for c in chars:
        	h = c + h * 31
    
    #Create the solver
    s = Solver()
    
    #Add condition: the final hash must equal our target value
    s.add(h == 1741233685)
    
    #Constrain characters to printable ASCII symbols (from 32 to 126)
    for c in chars:
        	s.add(c >= 32, c <= 126)
    
    #Run the search
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


algo2.py for second 8 bytes.

    from z3 import *
    
    #Create 8 symbolic variables (one for each of the 8 bytes of the second block)
    chars = [BitVec(f'b_{i}', 32) for i in range(8)]
    
    #Initial value of uVar1 (from previous assembly analysis: 0xDEADBEEF)
    uVar1 = 3735928559 
    DELTA = 2654435769  # 0x9e3779b9
    
    #Recreate the loop from the decompiled code
    for c in chars:
        	# Equivalent to: uVar1 = ((*ptr_to_buffer8 ^ uVar1) << 5 | uVar1 >> 0x1b) + 2654435769;
        	xor_val = c ^ uVar1
        	# Circular left shift by 5: (xor_val << 5) | (LShR(xor_val, 27))
        	rolled = (xor_val << 5) | LShR(xor_val, 27)
        	uVar1 = (rolled + DELTA)
        
        	# uVar1 = uVar1 >> 0x10 ^ uVar1;
        	uVar1 = LShR(uVar1, 16) ^ uVar1
    
    #Create the Z3 solver
    s = Solver()
    
    #Target value that uVar1 must reach
    s.add(uVar1 == 0xc5b6c81)
    
    #Constrain the characters to printable ASCII range (from ' ' (32) to '~' (126))
    for c in chars:
        	s.add(c >= 32, c <= 126)
    
    #Run the search
    if s.check() == sat:
        	model = s.model()
        	result_chars = []
        	for i in range(8):
            	val = model[chars[i]].as_long()
            	result_chars.append(chr(val))
        	print("Found second part of the key:", "".join(result_chars))
    else:
        	print("No solution found. Check initial value of uVar1 or character range.")

We run the scripts one at  a  time  and  get  two  lines:  Rs6"wOyi  and  0[tPXKXJ.

Launch crackme and enter all the characters in one line:

> xela@pcdeblin:~/crackme/crackmes/DeathTrap$ ./sysupdate  Enter serial: Rs6"wOyi0[tPXKXJ 
> Valid serial Join us : https://t.me/+blTRfHi8oKJiN2E0

We see the string "Valid serial", which means the crackme has been successfully resolved!

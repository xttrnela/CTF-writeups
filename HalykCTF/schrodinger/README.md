

## Schrodinger


Перед нами 64-битный исполняемый ELF файл:

    ┌──(kali㉿kali)-[~/halyk_ctf/schrodinger_task]
    └─$ file schrodinger 
    schrodinger: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, BuildID[sha1]=2bdef757ddec7f247084777ec5d0bea5596d1f1d, for GNU/Linux 3.2.0, stripped

После выдачи прав на исполнение( chmod u+x ) запустим файл и посмотрим на его поведение:

    ──(kali㉿kali)-[~/halyk_ctf/schrodinger_task]
    └─$ ./schrodinger              
    usage: ./schrodinger HalykCTF{...}

Добавим необходимый аргумент и произвольный текст внутри фигурных скобок:

    ┌──(kali㉿kali)-[~/halyk_ctf/schrodinger_task]
    └─$ ./schrodinger HalykCTF{aaa}
    the cat is dead.

Очевидно аргумент не прошел ту или иную проверку и выдал ошибку.

Теперь просматриваю текстовые последовательности через `strings -a`. На выходе можно проследить несколько интересных моментов:

Несмотря на то, что файл stripped, то есть в файле удалена отладочная информация , таблица символов и другая дополнительная информация, файл использует динамическую компоновку(dynamically linked), а значит имена функций будут отображены в секции .dynstr. Оттуда нам известны имена следующих функций:

> puts
> __stack_chk_fail
> __printf_chk 
> munmap 
> strlen 
> ptrace
> __libc_start_main 
> mprotect
> __cxa_finalize 
> mmap 
> strncmp

Особенно интересны функции `ptrace`, `mmap`, `munmap` и `mprotect`. Функция ptrace используется для контролем над другим процессом(трассировщик). Возможно, данная функция является некоторым анти-дебаггером, поскольку два трассировщика не могут наблюдать за одним процессом. Также, судя по факту использования функции mmap, можно предположить, что в адресное пространство процесса отображается область памяти, в котором выполняется основной код проверки нашей строки на валидность. Этому также свидетельствует функция mprotect, которая изменяет права доступа отображенной области памяти. munmap же используется для удаления отображенной области памяти. Чтобы проверить наши гипотезы, попробуем использовать утилиту `strace` для просмотра системных вызовов:

    ┌──(kali㉿kali)-[~/halyk_ctf/schrodinger_task]
    └─$ strace -f -e trace=ptrace,mmap,mprotect,munmap ./schrodinger 'HalykCTF{aaa}'
    mmap(NULL, 8192, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x7f5ffd0d6000
    mmap(NULL, 102014, PROT_READ, MAP_PRIVATE, 3, 0) = 0x7f5ffd0bd000
    mmap(NULL, 2055568, PROT_READ, MAP_PRIVATE|MAP_DENYWRITE, 3, 0) = 0x7f5ffcec7000
    mmap(0x7f5ffceef000, 1474560, PROT_READ|PROT_EXEC, MAP_PRIVATE|MAP_FIXED|MAP_DENYWRITE, 3, 0x28000) = 0x7f5ffceef000
    mmap(0x7f5ffd057000, 339968, PROT_READ, MAP_PRIVATE|MAP_FIXED|MAP_DENYWRITE, 3, 0x190000) = 0x7f5ffd057000
    mmap(0x7f5ffd0aa000, 24576, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_FIXED|MAP_DENYWRITE, 3, 0x1e3000) = 0x7f5ffd0aa000
    mmap(0x7f5ffd0b0000, 52624, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_FIXED|MAP_ANONYMOUS, -1, 0) = 0x7f5ffd0b0000
    mmap(NULL, 12288, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x7f5ffcec4000
    mprotect(0x7f5ffd0aa000, 16384, PROT_READ) = 0
    mprotect(0x563528066000, 4096, PROT_READ) = 0
    mprotect(0x7f5ffd115000, 8192, PROT_READ) = 0
    munmap(0x7f5ffd0bd000, 102014)          = 0
    ptrace(PTRACE_TRACEME)                  = -1 EPERM (Operation not permitted)
    mmap(NULL, 4096, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x7f5ffd0d5000
    mprotect(0x7f5ffd0d5000, 4096, PROT_READ|PROT_EXEC) = 0
    the cat is dead.
    munmap(0x7f5ffd0d5000, 4096)            = 0
    +++ exited with 1 +++

`ptrace` пытается занять слот трассировки, но поскольку `strace` сам является трассировщиком, выдает ошибку EPERM. Однако, пока мы не наблюдаем каких-то последствий, поскольку программа продолжила выполняться и выполнила отображение страницы равной 4096 байт, после чего устанавливает ей права на выполнение, и только после этого программа ловит неверный ввод и освобождает отображенную память через `munmap`.
Мы можем написать программу, которая вытащит данную страницу памяти в бинарный файл, чтобы просмотреть его код через дизассемблер/декомпилятор.
Для этого напишем динамическую библиотеку на C, которая скопирует машинный код в новый бинарник.

mprot_hook.c:

Подключаем необходимые заголовочные файлы. 

    #define _GNU_SOURCE
    
    #include <dlfcn.h>
    #include <errno.h>
    #include <fcntl.h>
    #include <stdint.h>
    #include <stdio.h>
    #include <stdlib.h>
    #include <sys/mman.h>
    #include <unistd.h>

Мы также используем макрос `_GNU_SOURCE` для расширения `RTLD_NEXT`, которое поможет нам найти реализацию функции `mprotect`. 

Переходим к реализации функции создания дампа памяти:

    static int dump_page(const void *addr, size_t len){
            char path[256];
            snprintf(path, sizeof(path), "exec_page.bin");
    
            int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
            if(fd < 0){
                    perror("open file");
                    return -1;
            }
    
            size_t written = 0;
            const uint8_t *buf = (const uint8_t *)addr;
            while(written < len){
                    ssize_t n = write(fd, buf + written, len - written);
                    if(n < 0){
                            if(errno == EINTR) continue;
                            perror("write");
                            close(fd);
                            return -1;
                    }
                    written += (size_t)n;
            }
    
            close(fd);
            fprintf(stdout, "hook dumped %zu bytes from %p to %s\n", len, addr, path);
            return 0;
    }

Наша функция принимает адрес памяти страницы и ее размер.
Затем создается массив для пути нашего будушего бинарника. 
Открываем файл в случае, если тот уже существует, и создаем если не существует. Открываем файл для записи и выдаем ему права 644.

size_t written = 0 является количеством записанных в файл байтов. Затем мы создается указатель, ссылающийся на память страницы. Мы приводим его в uint8_t, поскольку мы принимает указатель на void, а нам надо читать данные побайтово. Теперь в цикле записываем в наш файл каждый байт по адресу страницы. 

Теперь нам необходимо узнать адрес и размер страницы. Для этого мы напишем функцию, которая перехватит вызов функции `mprotect` , которая получает на вход необходимые нам данные, после чего выполним функцию для записи данных в бинарник:

    int mprotect(void *addr, size_t len, int prot){
            static int (*real_mprotect)(void *, size_t, int) = NULL;
            if(!real_mprotect){
                    real_mprotect = (int (*)(void *, size_t, int))dlsym(RTLD_NEXT, "mprotect");
            }

        int res = real_mprotect(addr, len, prot);
        if(res == 0 && (prot & PROT_EXEC)){
                size_t page_size = (size_t)sysconf(_SC_PAGESIZE);
                size_t to_dump;
                if(len < page_size && len > 0) to_dump = len;
                else to_dump = page_size;
                dump_page(addr, to_dump);
        }
        return res;
    }

Сначала мы создаем указатель на реальную функцию `mprotect`, затем получаем ее адрес через `dlsym`. Запускаем функцию и проверяем, действительно ли это область памяти с права на выполнение. Если да, получаем размер страницы и запускаем функцию `dump_page`.

Компилируем библиотеку и проверяем работу хука:

    ┌──(kali㉿kali)-[~/halyk_ctf/schrodinger_task]
    └─$ gcc -shared -fPIC mprot_hook.c -o mprot_hook.so -ldl
                                                                                                                                          
    ┌──(kali㉿kali)-[~/halyk_ctf/schrodinger_task]
    └─$ LD_PRELOAD=./mprot_hook.so ./schrodinger HalykCTF{aaa}
    hook dumped 4096 bytes from 0x7fa339525000 to exec_page.bin
    the cat is dead.

Мы прописываем в переменную LD_PRELOAD, чтобы передать нашу библиотеку первой. 
Как видно, мы получили наш файл. Теперь просмотим код бинарника. Для этого я использовал декомпилятор Ghidra. 
Мы получаем такую функцию:

    int FUN_00000000(int param_1,uint param_2)
    
    {
      sbyte sVar1;
      uint uVar2;
      
      uVar2 = 0x5c;
      if ((param_2 & 7) != 0) {
        sVar1 = (sbyte)(param_2 & 7);
        uVar2 = 0x5c >> (8U - sVar1 & 0x1f) | 0x5c << sVar1;
      }
      return (param_1 * -0x55 ^ uVar2) + param_2 * 0x11;
    }
В целом функция делает следующее:
Её можно представить так:

1.  Берёт два числа.
2.  Из второго числа извлекает три младших бита.
3.  На основе этих битов изменяет значение `0x5C` с помощью сдвигов.
4.  Умножает первое число на -85.
5.  Выполняет XOR с полученным значением.
6.  Прибавляет второе число, умноженное на 17.
7.  Возвращает результат.

Пока никакой ценнной информации ее реализация не представляет. 
После этого я дизассемблировал нашу исходную программу через `objdump -d -Mintel`, и обнаружил следующее:

    1196:       83 ff 02                cmp    edi,0x2
    1199:       75 09                   jne    11a4 <mprotect@plt+0x54>
    119b:       48 8b 46 08             mov    rax,QWORD PTR [rsi+0x8]
    119f:       48 89 44 24 08          mov    QWORD PTR [rsp+0x8],rax
    11a4:       c7 44 24 14 00 00 00    mov    DWORD PTR [rsp+0x14],0x0

В этом кусочке мы можем наблюдать проверку аргументов main, затем копирование второго аргумента массив argv, то есть нашей переданной строки HalykCTF{...}. 

Далее мы можем увидеть следующий участок:
```
123c:       48 8b 5c 24 08          mov    rbx,QWORD PTR [rsp+0x8]
1241:       ba 09 00 00 00          mov    edx,0x9
1246:       48 8d 35 e1 0d 00 00    lea    rsi,[rip+0xde1]        # 202e <mprotect@plt+0xede>
124d:       48 89 df                mov    rdi,rbx
1250:       e8 7b fe ff ff          call   10d0 <strncmp@plt>
1255:       85 c0                   test   eax,eax
1257:       0f 85 78 01 00 00       jne    13d5 <mprotect@plt+0x285>
```
Здесь первые 9 символов нашего вводимого аргумента сравниваются со строкой по адресу 0x202e. Это строка HalykCTF{. мы можем убедиться в этом выполнив:

    ──(kali㉿kali)-[~/halyk_ctf/schrodinger_task]
    └─$ xxd -s 0x202e -l 9 schrodinger
    0000202e: 4861 6c79 6b43 5446 7b                   HalykCTF{

Далее происходит сравнение символа по 27 индексу
с символом }, которая завершает флаг:
```
125d:       80 7b 1b 7d             cmp    BYTE PTR [rbx+0x1b],0x7d
1261:       0f 85 6e 01 00 00       jne    13d5 <mprotect@plt+0x285>
```
Того оставшееся число символов внутри фигурных скобок равно 18.

Теперь разбираем следующий участок:

    1280:       45 31 f6                xor    r14d,r14d
    1283:       4c 8d 64 24 30          lea    r12,[rsp+0x30]
    1288:       48 8d 5c 24 50          lea    rbx,[rsp+0x50]
    128d:       0f 1f 00                nop    DWORD PTR [rax]
    1290:       43 0f b6 3c 34          movzx  edi,BYTE PTR [r12+r14*1]
    1295:       44 89 f6                mov    esi,r14d
    1298:       ff d5                   call   rbp
    129a:       42 88 04 33             mov    BYTE PTR [rbx+r14*1],al
    129e:       49 83 c6 01             add    r14,0x1
    12a2:       49 83 fe 12             cmp    r14,0x12
    12a6:       75 e8                   jne    1290 <mprotect@plt+0x140>

Здесь мы видим вызов функции по адресу внутри регистра rbp. 
Сначала инициализируется счетчик r14. Далее мы получаем адреса буферов  
```
lea r12,[rsp+0x30]
lea rbx,[rsp+0x50]
```
Затем мы получаем текущий символ нашей строки из 18 символов:

```
movzx edi,BYTE PTR [r12+r14]
```
Где r12 - адрес начала нашей строки

Передаем индекс:
```
mov esi,r14d
```
После чего вызывается функция. Судя по всему, это та самая функция, которую мы обнаружили в отображенной странице с правами на выполнение.
И так цикл работает 18 раз, об этом свидетельствует строка:

    12a2:       49 83 fe 12             cmp    r14,0x12
Где 0x12 = 18.
Таким образом, программа берет 18 символов внутри фигурных скобок флага HalykCTF{...} и проводит некоторые преобразования над каждым символом.
Осталось выяснить, с какими значениями она сравнивает результат.

Разбираем данный участок:

	    11da:       31 c0                   xor    eax,eax
        11dc:       4c 8d 64 24 70          lea    r12,[rsp+0x70]
        11e1:       48 8d 35 b0 0e 00 00    lea    rsi,[rip+0xeb0]        # 2098 <mprotect@plt+0xf48>
        11e8:       48 8d 0d 91 0e 00 00    lea    rcx,[rip+0xe91]        # 2080 <mprotect@plt+0xf30>
        11ef:       90                      nop
        11f0:       48 89 c2                mov    rdx,rax
        11f3:       83 e2 07                and    edx,0x7
        11f6:       0f b6 14 16             movzx  edx,BYTE PTR [rsi+rdx*1]
        11fa:       32 14 01                xor    dl,BYTE PTR [rcx+rax*1]
        11fd:       41 88 14 04             mov    BYTE PTR [r12+rax*1],dl
        1201:       48 83 c0 01             add    rax,0x1
        1205:       48 83 f8 12             cmp    rax,0x12
        1209:       75 e5                   jne    11f0 <mprotect@plt+0xa0>
Этот участок особенно важен, потому что именно здесь формируется массив эталонных значений.

Сначала программа выполняет:

	    11e1:       48 8d 35 b0 0e 00 00    lea    rsi,[rip+0xeb0]        # 2098 <mprotect@plt+0xf48>
        11e8:       48 8d 0d 91 0e 00 00    lea    rcx,[rip+0xe91]        # 2080 <mprotect@plt+0xf30>
В комментариях дизассемблера указаны адреса, на которые ссылаются эти инструкции.

Получается:
`rsi` указывает на область данных по адресу `0x2098`;
 `rcx` указывает на область данных по адресу `0x2080`.
Это означает, что программа использует две области памяти, содержащие исходные байты.
Чтобы получить их содержимое, используем `xxd`:

    ┌──(kali㉿kali)-[~/halyk_ctf/schrodinger_task]
    └─$ xxd -g 1 -s 0x2098 -l 16 schrodinger                            
    00002098: 5a 3c 91 e7 12 88 6d f0 c0 bf 2f 44 87 17 c2 45  Z<....m.../D...E
                                                                                                                                                                                                                                          
    ┌──(kali㉿kali)-[~/halyk_ctf/schrodinger_task]
    └─$ xxd -g 1 -s 0x2080 -l 18 schrodinger
    00002080: 21 e8 b2 50 31 d9 52 24 98 62 9b ae c5 5f ae b0  !..P1.R$.b..._..
    00002090: 00 d0  
```
```

    00002098: 5a 3c 91 e7 12 88 6d f0 c0 bf 2f 44 87 17 c2 45

```

00002080: 21 e8 b2 50 31 d9 52 24 98 62 9b ae c5 5f ae b0
00002090: 00 d0
```
Итого мы получили все данные, необходимые для восстановления эталонного массива.

Теперь Проанализируем цикл формирования массива.

Инициализируется счетчик eax.
В `edx` помещается индекс, ограниченный тремя младшими битами:

    11f0:       48 89 c2                mov    rdx,rax

Затем:

    11f6:       0f b6 14 16             movzx  edx,BYTE PTR [rsi+rdx*1]

Из первой области данных считывается байт по индексу i & 7.

Слующая инструкция выполняет xor полученного байта с байтом из второй области данных по индексу i.
И в конце цикла счётчик увеличивается, а цикл повторяется до тех пор, пока не будет обработано 18 байт.

Того получается, что в бинарнике не хранится готовый массив. Программа самостоятельно формирует его во время выполнения.

Из анализа программы мы получили:

Известные данные:
1. длина внутренней части флага - 18 символов
2. индекс каждого символа - от 0 до 17
3. функция преобразования символа
4. массив `target` из 18 байтов

Неизвестные данные - сами 18 символов.

Программа проверяет каждый символ независимо от остальных.

В финале создаем скрипт для восстановления флага по указанным данным. Важно: мы самостоятельно восстановим их из байтов `.rodata`, повторив алгоритм, обнаруженный в ассемблере:

    "Скрипт написан с помощью ИИ"
    def rotl8(val: int, shift: int) -> int:
        shift &= 7
        val &= 0xFF
        return ((val << shift) | (val >> (8 - shift))) & 0xFF
    
    
    def jit_eval(c: int, idx: int) -> int:
        s = idx & 7
        u_var2 = rotl8(0x5C, s) if s != 0 else 0x5C
        term1 = ((c * (-0x55)) ^ u_var2) & 0xFF
        term2 = (idx * 0x11) & 0xFF
        return (term1 + term2) & 0xFF
    
    
    table = bytes.fromhex("21e8b25031d9522498629baec55faeb000d0")
    key = bytes.fromhex("5a3c91e712886df0")
    
    targets = [table[i] ^ key[i % 8] for i in range(18)]
    
    chars = []
    for idx in range(18):
        matches = [chr(c) for c in range(32, 127) if jit_eval(c, idx) == targets[idx]]
        print(f"idx={idx:02d}: target=0x{targets[idx]:02x} -> {matches}")
        chars.append(matches[0] if len(matches) == 1 else "?")
    
    flag = "HalykCTF{" + "".join(chars) + "}"
    print("Candidate flag:", flag)
Запускаем скрипт и забираем флаг:

    ┌──(kali㉿kali)-[~/halyk_ctf/schrodinger_task]
    └─$ python3 flag.py 
    idx=00: target=0x7b -> ['u']
    idx=01: target=0xd4 -> ['q']
    idx=02: target=0x23 -> ['P']
    idx=03: target=0xb7 -> ['2']
    idx=04: target=0x23 -> ['N']
    idx=05: target=0x51 -> ['e']
    idx=06: target=0x3f -> ['j']
    idx=07: target=0xd4 -> ['Y']
    idx=08: target=0xc2 -> ['2']
    idx=09: target=0x5e -> ['w']
    idx=10: target=0x0a -> ['3']
    idx=11: target=0x49 -> ['D']
    idx=12: target=0xd7 -> ['j']
    idx=13: target=0xd7 -> ['S']
    idx=14: target=0xc3 -> ['F']
    idx=15: target=0x40 -> ['M']
    idx=16: target=0x5a -> ['B']
    idx=17: target=0xec -> ['Y']
    Candidate flag: HalykCTF{uqP2NejY2w3DjSFMBY}


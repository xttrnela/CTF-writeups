#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>

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


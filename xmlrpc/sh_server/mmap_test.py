#Lukas - 16.05.2018 - TEST SCRIPT, NOT IN USE
#First attempt at accessing the FPGA-registers using mmap. This is based on the existing PID-App written in C (Files "fpga_pid.c" and "fpga_pid.h"). Approach was not successful.

import mmap
import os

f = open("/dev/mem", "r+b")

page_size=os.sysconf("SC_PAGE_SIZE")
page_addr = 0x40300000 & (~(page_size-1))
size = 0x100

pid_reg = mmap.mmap(f.fileno(), size, mmap.MAP_SHARED, mmap.PROT_READ , offset = page_addr)

print ("Teschd1")

pid_reg.close()
f.close()

print ("Teschd2")
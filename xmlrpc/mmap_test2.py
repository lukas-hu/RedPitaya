# Lukas - 16.05.18 - TEST SCRIPT, NOT IN USE
# Successful attempt at accessing the FPGA-Registers. Code taken from http://forum.redpitaya.com/viewtopic.php?f=14&t=1784&p=6978&hilit=mmap+python#p6966 
# Code generates the mmap and lets the LEDs blink 10 times. See newer scripts for detailled explanations of the functions.

import mmap
import os
import time
import numpy as np

regset_hk = np.dtype([
    ('id'          , 'uint32'),
    ('dna_lo'      , 'uint32'),
    ('dna_hi'      , 'uint32'),
    ('digital_loop', 'uint32'),
    ('ex_cd_p'     , 'uint32'),
    ('ex_cd_n'     , 'uint32'),
    ('ex_co_p'     , 'uint32'),
    ('ex_co_n'     , 'uint32'),
    ('ex_ci_p'     , 'uint32'),
    ('ex_ci_n'     , 'uint32'),
    ('reserved_2'  , 'uint32'),
    ('reserved_3'  , 'uint32'),
    ('led_control' , 'uint32')
])

os.system('cat /opt/redpitaya/fpga/fpga_0.94.bit > /dev/xdevcfg')

fd = os.open('/dev/mem', os.O_RDWR)
m = mmap.mmap(fileno=fd, length=mmap.PAGESIZE, offset=0x40000000)
hk_array = np.recarray(1, regset_hk, buf=m)
hk = hk_array[0]

for i in range(10):
    hk.led_control = 0xff
    time.sleep(0.2)
    hk.led_control = 0x00
    time.sleep(0.2)

m.close()

print("teshd")
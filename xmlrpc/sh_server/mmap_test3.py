# Lukas - 16.05.18 - TEST SCRIPT, NOT IN USE
# Successful attempt at accessing the FPGA registers of the PID based on http://forum.redpitaya.com/viewtopic.php?f=14&t=1784&p=6978&hilit=mmap+python#p6966 
# Code generates the mmap, sets setpoint, integrator and reset parameters, waits 10s and sets them to 0 again

import mmap
import os
import time
import numpy as np

# Create object setting the datatype of every parameter to 32-bit unsigned int. The ordering of the parameters is based on the RedPitaya Memory Map
regset_hk = np.dtype([
    ('config'        , 'uint32'),
    ('reserved_1'    , 'uint32'),
    ('reserved_2'    , 'uint32'),
	('reserved_3'    , 'uint32'),
    ('Sp11'          , 'uint32'),
    ('Kp11'          , 'uint32'),
    ('Ki11'          , 'uint32'),
    ('Kd11'          , 'uint32'),
	('Sp12'          , 'uint32'),
    ('Kp12'          , 'uint32'),
    ('Ki12'          , 'uint32'),
    ('Kd12'          , 'uint32'),
	('Sp21'          , 'uint32'),
    ('Kp21'          , 'uint32'),
    ('Ki21'          , 'uint32'),
    ('Kd21'          , 'uint32'),
	('Sp22'          , 'uint32'),
    ('Kp22'          , 'uint32'),
    ('Ki22'          , 'uint32'),
    ('Kd22'          , 'uint32')
])

# Load the required image (fpgav0.94_sh6.bit) to the FPGA
os.system('cat /opt/redpitaya/fpga/fpgav0.94_sh6.bit > /dev/xdevcfg')

# Create the mmap and use it as buffer for a numpy array which can be modified. The offset parameter determines which part of the register is accessed (PID in this case), see the Memory Map for details.
fd = os.open('/dev/mem', os.O_RDWR)
m = mmap.mmap(fileno=fd, length=mmap.PAGESIZE, offset=0x40300000)
hk_array = np.recarray(1, regset_hk, buf=m)
hk = hk_array[0]

print("teschd1")

#Enable the PID: Set both Setpoint and Ki to 1000 and the reset parameter (first 4 bits of configuration parameter) to 0. Numbers are given in Hex format
hk.config = 0x000 
hk.Sp12 = 0x3e8
hk.Ki12 = 0x3e8
#Wait 10s
time.sleep(10)
#Disable the PID
hk.Sp12 = 0x000
hk.Ki12 = 0x000

#Close the mmap
m.close()

print("teschd2")
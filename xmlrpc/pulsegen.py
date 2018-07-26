import mmap
import os
import numpy as np
import time

os.system('cat /opt/redpitaya/fpga/fpgav0.94_pg_final.bit > /dev/xdevcfg')

test=[]
for i in range(0,1024):
	test.append(('asdf'+str(i),'uint32'))
	
regset = np.dtype(test)
regset2 = np.dtype([('spdelay1','uint32'),('ki','uint32'),('reset','uint32'),('ch1set','uint32'),('spdelay2','uint32'),('offset','uint32'),('offsetmeas','uint32'),('offmode','uint32')])

fd = os.open('/dev/mem', os.O_RDWR)
m = mmap.mmap(fileno=fd, length=mmap.PAGESIZE, offset=0x40601000)
params_array = np.recarray(1, regset, buf=m)
wave1params = params_array[0] #waveform used for pgen and error 

m2 = mmap.mmap(fileno=fd, length=mmap.PAGESIZE, offset=0x40600000)
params_array2 = np.recarray(1, regset2, buf=m2)
params2 = params_array2[0]

m3 = mmap.mmap(fileno=fd, length=mmap.PAGESIZE, offset=0x40602000)
params_array3 = np.recarray(1, regset, buf=m3)
wave2params = params_array3[0] #waveform used for pid_out

waveform=[]

for i in range(0,1024):
	#setattr(wave1params,('asdf'+str(i)),0)
	setattr(wave1params,('asdf'+str(i)),int(1500*np.exp(-((i-500)**2)/(2*10000))))
	#waveform.append(282*np.exp(-((i-500)**2)/(2*100000)))

#for i in range(501,1024):
#	setattr(wave1params,('asdf'+str(i)),0)


for i in range(0,1024):
	#setattr(wave2params,('asdf'+str(i)),100000)
	setattr(wave2params,('asdf'+str(i)),int(16383*np.exp(-((i-500)**2)/(2*10000))))

#for i in range(501,1024):
#	setattr(wave2params,('asdf'+str(i)),0)

	
params2.spdelay1 = 45
params2.ki = 100
params2.reset = 0
params2.ch1set = 2 #0: pid_out, 1: int_out, 2: error, 3: pgen_out
params2.spdelay2 = 0
params2.offset = 1000
params2.offsetmode = 1
print(max(wave2params))
	
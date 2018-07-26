# Lukas - 17.05.18
# testing data acquisition from the inputs with the RedPitaya aqcuire command line function
import os
import numpy as np

acquire=os.popen('acquire 100 1').read()
fulldata = np.zeros(0)
for t in acquire.split():
    try:
        fulldata=np.append(fulldata,(int(t)))
    except ValueError:
        pass
data_ch2 = fulldata[1::2]
condition = data_ch2 > (np.amax(data_ch2)- 0.3*abs(np.amax(data_ch2)-np.amin(data_ch2)))
data_ch2_high = data_ch2[condition]
print(data_ch2)
print(float(np.mean(data_ch2_high)))

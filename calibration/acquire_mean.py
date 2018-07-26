# Lukas - 17.05.18
# testing data acquisition from the inputs with the RedPitaya aqcuire command line function
import os
import numpy as np

acquire=os.popen('acquire 16000 1').read()
fulldata = np.zeros(0)
for t in acquire.split():
    try:
        fulldata=np.append(fulldata,(int(t)))
    except ValueError:
        pass
data_ch1 = fulldata[0::2]
data_ch2 = fulldata[1::2]
print(float(np.mean(data_ch1)))
print(float(np.mean(data_ch2)))

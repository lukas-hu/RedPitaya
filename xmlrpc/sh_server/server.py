# Lukas - 24.05.18 
# XML-RPC Server to be run on the RedPitaya based on the previous mmap tests and https://docs.python.org/3.1/library/xmlrpc.server.html
# Script creates mmap to FPGA registers, defines functions that set/modify the PID parameters and acquire input data and launches the server

import mmap
import os
import numpy as np
import time
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler

# Create object setting the datatype of every parameter to 32-bit unsigned int. The ordering and usage of the parameters is based on the RedPitaya Memory Map, 
# which is engineered for four PID modules. In the sample&hold+delay PID, only the PID12-module is being used. This server thus only modifies the respective parameters in the register. 
regset = np.dtype([
    ('config'        , 'uint32'), #Bits 1-4 trigger the integrator reset of the four PID-modules. 1 means the integrator is being reset, 0 means no reset.
    ('reserved_1'    , 'uint32'), #unused in this script
    ('reserved_2'    , 'uint32'), #unused in this script
	('reserved_3'    , 'uint32'), #unused in this script
    ('Sp11'          , 'uint32'), #unused in this script
    ('Kp11'          , 'uint32'), #unused in this script
    ('Ki11'          , 'uint32'), #unused in this script
    ('Kd11'          , 'uint32'), #unused in this script
	('Sp12'          , 'uint32'), #PID setpoint
    ('Kp12'          , 'uint32'), #PID Kp
    ('Ki12'          , 'uint32'), #PID Ki
    ('Kd12'          , 'uint32'), #PID Kd
	('Sp21'          , 'uint32'), #unused in this script
    ('Kp21'          , 'uint32'), #unused in this script
    ('Ki21'          , 'uint32'), #PID delay2
    ('Kd21'          , 'uint32'), #PID delay1
	('Sp22'          , 'uint32'), #unused in this script
    ('Kp22'          , 'uint32'), #unused in this script
    ('Ki22'          , 'uint32'), #unused in this script
    ('Kd22'          , 'uint32')  #unused in this script
])

# Load the required image (fpgav0.94_sh6.bit) to the FPGA
os.system('cat /opt/redpitaya/fpga/fpgav0.94_sh6.bit > /dev/xdevcfg')

# Create the mmap and use it as buffer for a numpy array which can be modified. 
# The offset parameter determines which part of the register is accessed (PID in this case), see the Memory Map for details
fd = os.open('/dev/mem', os.O_RDWR)
m = mmap.mmap(fileno=fd, length=mmap.PAGESIZE, offset=0x40300000)
params_array = np.recarray(1, regset, buf=m)
params = params_array[0]

 # measured ADC calibration values for HV input jumper setting. Parameters are ["ADC offset", "ADC counts/Volt"]
calib = np.array([-167.81, 282.209])

 # Set setpoint to offset value of ADC
params.Sp12 = calib[0]

# Define function that assigns input values to PID parameters in the register. If the values are input in decimal form, there is no need for conversion because the datatype is numpy uint32 already
def pid_set_values(res, sp, kp, ki, kd, d1, d2, hv):
	if res == True:			
		params.config = 0xFFFFFFFF		# set all bits to 1 to ensure reset of all PIDS (slight overkill maybe)
	else:
		params.config = 0x0
		
	# switch between the measured calibrations for HV and LV input jumper setting
	if hv == True:						
		calib[0] = -167.81
		calib[1] = 282.209
	else:
		calib[0] = -196.228
		calib[1] = 7231.4
		
	params.Sp12 = sp*calib[1] + calib[0]
	
	params.Kp12 = kp
	params.Ki12 = ki
	params.Kd12 = kd
	params.Kd21 = int(round(d1/8))		# d1 is input in nanoseconds, one clock cycle is 8ns. Delay in register should be given in clock cycles
	params.Ki21 = int(round(d2/8))		# d2 is input in nanoseconds, one clock cycle is 8ns. Delay in register should be given in clock cycles
	return

 # Define function that reads the current PID-params from memory. The integrator reset is converted to a boolean type variable for easy handling in the client	
def pid_get_values():
	# Setpoint is an unsigned int in 2's complement -> convert negative 2's complement values to negative phyton ints
	if (len(np.binary_repr(params.Sp12)) == 14) & (np.binary_repr(params.Sp12)[0] == '1'): # if first bit of the setpoint (length in fpga:14 bit) is 1, setpoint is negative 
		sp_cnts = -int(''.join('1' if x == '0' else '0' for x in np.binary_repr(params.Sp12 - 0b1)),2) # fancy conversion following wikipedia.de/Zweierkomplement
	else:
		sp_cnts = int(params.Sp12)
	sp = (sp_cnts - calib[0])/calib[1]
	
	res = bin(params.config)[2]=='1' 
	
	return [bool(res), float(sp), int(params.Kp12), int(params.Ki12), int(params.Kd12), float(params.Kd21*8), float(params.Ki21*8)]
	
# Define function that sets the PID parameters to 0 and enables automatic reset of the integrator 
def pid_reset():
	params.config = 0xFFFFFFFF
	params.Sp12 = calib[0]
	params.Kp12 = 0x0
	params.Ki12 = 0x0
	params.Kd12 = 0x0
	params.Kd21 = 0x0
	params.Ki21 = 0x0
	return	

# Define function that acquires samples from the oscilloscope input buffer, selects the data of channel2 and returns the mean	
def acquire_signal():
	acquire=os.popen('acquire 100 1').read()		# Acquisition with the acquire command of the RedPitaya. Syntax: 'acquire "number of samples" "decimation"'
	fulldata = np.zeros(0)
	for t in acquire.split():						# This loop selects the numbers from the data string containing standard characters
		try:
			fulldata=np.append(fulldata,(int(t)))
		except ValueError:
			pass
	data_ch2 = fulldata[1::2]						# Select channel 2 data
	
	#select datapoints above a certain threshold close to the maximum to obtain correct mean in pulsed operation
	condition = data_ch2 > (np.amax(data_ch2)- 0.3*abs(np.amax(data_ch2)-np.amin(data_ch2))) 	
	data_ch2_high = data_ch2[condition]
	
	return float((np.mean(data_ch2_high)-calib[0])/calib[1])
	

# Launch the server. The rest of the code is essentially copy&pasted
# Restrict to a particular path
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

# Create server, use RedPitayas IP
server = SimpleXMLRPCServer(("130.183.94.184", 8000), requestHandler=RequestHandler, allow_none=True)
server.register_introspection_functions()	

# Register the functions defined above so they can be called by client
server.register_function(pid_set_values)
server.register_function(pid_reset)
server.register_function(acquire_signal)
server.register_function(pid_get_values)

try:
	print("Server started")
	print('Use Control-C to exit')
	server.serve_forever() #Enter server main loop
except KeyboardInterrupt:
	print('Exiting')
	pid_reset() 
	m.close()
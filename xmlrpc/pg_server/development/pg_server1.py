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
controller_regset = np.dtype([
    ('Delay1'        , 'uint32'), #Delay start of error signal calculation to account for finite runtime of electronic signal and rise time of AOM.
    ('Ki'    		 , 'uint32'), #Gain of the integrator
    ('Reset'         , 'uint32'), #Bit 1 triggers the integrator reset of the four PID-modules. 1 means the integrator is being reset, 0 means no reset.
	('Ch1set'        , 'uint32'), #Set output mode of channel 1 (see FPGA code for details). Unused by Server&Client
    ('Delay2'        , 'uint32'), #Delay conclusion of error signal calculation to account for finite runtime of electronic signal and rise time of AOM.
    ('Offset'        , 'uint32'), #Give an ADC offset for the error signal calculation to calibrate. Can be enabled via 'Offsetmode' parameter
    ('Offsetmeas'    , 'uint32'), #ADC Offset measured by the FPGA. Read-only. 
    ('Offsetmode'    , 'uint32'), #Switch between measuring the offset or setting it manually. 
	('Avg_Int'       , 'uint32')  #Averaged integrator output for monitoring functionality of controller
])

waveform_list=[]
for i in range(0,1024):
	waveform_list.append((str(i),'uint32'))
waveform_regset = np.dtype(waveform_list)

# Load the required image (fpgav0.94_sh6.bit) to the FPGA
os.system('cat /opt/redpitaya/fpga/fpgav0.94_pg_74.bit > /dev/xdevcfg')

# Create the mmap and use it as buffer for a numpy array which can be modified. 
# The offset parameter determines which part of the register is accessed (PID in this case), see the Memory Map for details
fd = os.open('/dev/mem', os.O_RDWR)
m = mmap.mmap(fileno=fd, length=mmap.PAGESIZE, offset=0x40600000)
controller_params_array = np.recarray(1, controller_regset, buf=m)
cont_params = controller_params_array[0]

m2 = mmap.mmap(fileno=fd, length=mmap.PAGESIZE, offset=0x40602000)
waveform1_array = np.recarray(1, waveform_regset, buf=m2)
waveform1 = waveform1_array[0]

m3 = mmap.mmap(fileno=fd, length=mmap.PAGESIZE, offset=0x40604000)
waveform2_array = np.recarray(1, waveform_regset, buf=m3)
waveform2 = waveform2_array[0]

 # measured ADC calibration values for HV input jumper setting. Parameters are ["ADC offset", "ADC counts/Volt"]
calib = np.array([-167.81, 282.209])


# Define function that assigns input values to PID parameters in the register. If the values are input in decimal form, there is no need for conversion because the datatype is numpy uint32 already
def pg_set_values(res, amp, wave, ki, d1, d2, hv, ch1mode, offsetmode, offset):
	if res == True:			
		cont_params.Reset = 0x1		
	else:
		cont_params.Reset = 0x0
		
	# switch between the measured calibrations for HV and LV input jumper setting
	if hv == True:						
		calib[0] = -167.81
		calib[1] = 282.209
	else:
		calib[0] = -196.228
		calib[1] = 7231.4
	
	# set offset measurement mode
	if offsetmode == True:
		cont_params.Offsetmode = 1
	else:
		cont_params.Offsetmode = 0
		if offset >=0:
			cont_params.Offset = offset
		else:
			cont_params.Offset = (offset & 0b11111111111111) # convert to signed 2's complement
	
	# compute normalized and unnormalized waveforms
	for i in range(0,1024):
		setattr(waveform1,str(i),int(round((amp*calib[1] + calib[0])*wave[i])))
	
	for i in range(0,1024):
		setattr(waveform2,str(i),int(16383*wave[i]))
	
	cont_params.Ch1set = ch1mode
	cont_params.Ki = ki
	cont_params.Delay1 = int(round(d1/8))		# d1 is input in nanoseconds, one clock cycle is 8ns. Delay in register should be given in clock cycles
	cont_params.Delay2 = int(round(d2/8))		# d2 is input in nanoseconds, one clock cycle is 8ns. Delay in register should be given in clock cycles
	return

 # Define function that reads the current PID-params from memory. The integrator reset is converted to a boolean type variable for easy handling in the client	
def pg_get_values():
	# Amplitude is an unsigned int in 2's complement -> convert negative 2's complement values to negative phyton ints
	amp_reg = max(waveform1)
	if (len(np.binary_repr(amp_reg)) == 14) & (np.binary_repr(amp_reg)[0] == '1'): # if first bit of the setpoint (length in fpga:14 bit) is 1, setpoint is negative 
		amp_cnts = -int(''.join('1' if x == '0' else '0' for x in np.binary_repr(amp_reg - 0b1)),2) # fancy conversion following wikipedia.de/Zweierkomplement
	else:
		amp_cnts = int(amp_reg)
	amp = round((amp_cnts - calib[0])/calib[1],3)
	
	res = bin(cont_params.Reset)[2]=='1' 
	
	# Manually set offset is an unsigned int in 2's complement -> convert negative 2's complement values to negative phyton ints
	if (len(np.binary_repr(cont_params.Offset )) == 14) & (np.binary_repr(cont_params.Offset )[0] == '1'): # if first bit of the setpoint (length in fpga:14 bit) is 1, setpoint is negative 
		offset = -int(''.join('1' if x == '0' else '0' for x in np.binary_repr(cont_params.Offset  - 0b1)),2) # fancy conversion following wikipedia.de/Zweierkomplement
	else:
		offset = int(cont_params.Offset)
	offsetmode = cont_params.Offsetmode == 1
	
	# integrator output is an unsigned int in 2's complement -> convert negative 2's complement values to negative phyton ints
	if (len(np.binary_repr(cont_params.Avg_Int )) == 14) & (np.binary_repr(cont_params.Avg_Int )[0] == '1'): # if first bit of the setpoint (length in fpga:14 bit) is 1, setpoint is negative 
		avg_int = -int(''.join('1' if x == '0' else '0' for x in np.binary_repr(cont_params.Avg_Int  - 0b1)),2) # fancy conversion following wikipedia.de/Zweierkomplement
	else:
		avg_int = int(cont_params.Avg_Int)
	
	d1 = cont_params.Delay1*8
	d2 = cont_params.Delay2*8
	
	return [bool(res), float(amp), int(cont_params.Ki), int(d1), int(d2), bool(offsetmode), int(offset), int(avg_int)]
	
# Define function that sets the PID parameters to 0 and enables automatic reset of the integrator 
def cont_reset():
	cont_params.Reset = 0x1
	cont_params.Ki = 0
	cont_params.Delay1 = 0
	cont_params.Delay2 = 0
	cont_params.Offset = 0
	return		

# Launch the server. The rest of the code is essentially copy&pasted
# Restrict to a particular path
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

# Create server, use RedPitayas IP
server = SimpleXMLRPCServer(("130.183.94.184", 8000), requestHandler=RequestHandler, allow_none=True)
server.register_introspection_functions()	

# Register the functions defined above so they can be called by client
server.register_function(pg_set_values)
server.register_function(cont_reset)
server.register_function(pg_get_values)

try:
	print("Server started")
	print('Use Control-C to exit')
	server.serve_forever() #Enter server main loop
except KeyboardInterrupt:
	print('Exiting')
	cont_reset() 
	m.close()
	m2.close()
	m3.close()
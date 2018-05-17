# Lukas - 16.05.18 
# XML-RPC Server to be run on the RedPitaya based on the previous mmap tests and https://docs.python.org/3.1/library/xmlrpc.server.html
# Script creates mmap to FPGA registers, defines a function that sets the PID parameters and launches the server

import mmap
import os
import numpy as np
import time
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler

# Create object setting the datatype of every parameter to 32-bit unsigned int. The ordering of the parameters is based on the RedPitaya Memory Map.
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

# Create the mmap and use it as buffer for a numpy array which can be modified. The offset parameter determines which part of the register is accessed (PID in this case), see the Memory Map for details
fd = os.open('/dev/mem', os.O_RDWR)
m = mmap.mmap(fileno=fd, length=mmap.PAGESIZE, offset=0x40300000)
hk_array = np.recarray(1, regset_hk, buf=m)
hk = hk_array[0]

# Simple function that assigns input values to PID parameters in the register. If the values are input in decimal form, there is no need for conversion to hex.
def pid_set_values(res, sp, kp, ki, kd, d1, d2):
	hk.config = res
	hk.Sp12 = sp
	hk.Kp12 = kp
	hk.Ki12 = ki
	hk.Kd12 = kd
	hk.Kd21 = d1
	hk.Ki21 = d2
	return

# Launch the server. This is essentially copy&pasted
# Restrict to a particular path
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

# Create server, use RedPitayas IP
server = SimpleXMLRPCServer(("130.183.94.184", 8000), requestHandler=RequestHandler, allow_none=True)
server.register_introspection_functions()	

# Register the function that was defined above so it can be called by client
server.register_function(pid_set_values)

print("Server started")

try:
    print('Use Control-C to exit')
    server.serve_forever() #Enter server main loop
except KeyboardInterrupt:
	print('Exiting')
	pid_set_values(0,0,0,0,0,0,0) #Reset PID
	m.close()
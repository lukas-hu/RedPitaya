# Lukas - 16.05.18 
# First successful attempt at creating a client based on https://docs.python.org/3.1/library/xmlrpc.server.html
# Script initializes server, enables the PID via the pid_set_values function, waits for the enter key, resets and exits

import xmlrpc.client

s = xmlrpc.client.ServerProxy('http://130.183.94.184:8000')

print("Initialized")

s.pid_set_values(0,1000,0,1000,0,0,0) #Setpoint=1000, Ki=1000
input("Enter to exit...")
s.pid_set_values(0,0,0,0,0,0,0)

print("Exiting")
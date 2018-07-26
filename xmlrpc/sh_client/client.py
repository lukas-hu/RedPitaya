# Lukas - 24.05.18 
# xmlrpc-client based on https://docs.python.org/3.1/library/xmlrpc.server.html and interface with TraitsUI. Script is written for Phython2

import xmlrpclib  # Different in Python3
from traits.api import HasTraits, Button, Int, Float, String, Bool, Range, Enum
from traitsui.api import View, Item, HGroup, VGroup, Spring, ImageEnumEditor
from threading import Thread
import time
import os

class LockStatusThread(Thread):
	def run(self):
		while not self.wants_abort:
			self.master.update_status()
			time.sleep(1)

class PIDClient(HasTraits):
	# define traits
	setpoint = Float(0, desc="setpoint of the PID in Volts") 
	k_i = Range(0, 2**13 - 1, 600, desc="integration gain of the PID controller") 
	k_p = Range(0, 2**13 - 1, 0, desc="proportional gain of the PID controller")
	k_d = Range(0, 2**13 - 1, 0, desc="differential gain of the PID controller")
	integrator_reset = Bool(False, desc="reset the integrator")
	hv_input = Bool(True, desc="specify if the input jumper is on hv or not")
	sah_delay_1 = Float(500, desc="rising edge sample and hold delay in ns")
	sah_delay_2 = Float(500, desc="falling edge sample and hold delay in ns")
	send_changes = Button()
	mean_value = Float(0, desc="mean value of redpitaya's input in Volts")
	pid_reset = Button()
	onlock_image = Enum(['lock'], editor=ImageEnumEditor(path=os.getcwd()))
	not_onlock_image = Enum(['nolock'], editor=ImageEnumEditor(path=os.getcwd()))
	onlock = Bool(False)
	
	# create Traits view
	traits_view = View( VGroup(
								VGroup( HGroup("setpoint",Spring()), HGroup("k_p", "k_i", "k_d"), HGroup("integrator_reset", "hv_input"), HGroup("sah_delay_1", "sah_delay_2")), 
								HGroup("send_changes", "pid_reset", Spring()),
								Item("mean_value", style="readonly"), VGroup(Item("onlock_image", show_label=False, style='readonly', visible_when='onlock'),
								Item("not_onlock_image", show_label=False, style='readonly', visible_when='not onlock'), Spring() ) ), resizable=True, title="RedPitaya PID-Client 3000")
								
	def __init__(self, address='http://130.183.94.184:8000'):
		# create server proxy
		self.client = xmlrpclib.ServerProxy(address)
		
		# get current PID parameters
		self.integrator_reset = self.client.pid_get_values()[0]
		self.setpoint = self.client.pid_get_values()[1]
		self.k_p = self.client.pid_get_values()[2]
		self.k_i = self.client.pid_get_values()[3]
		self.k_d = self.client.pid_get_values()[4]
		self.sah_delay_1 = self.client.pid_get_values()[5]
		self.sah_delay_2 = self.client.pid_get_values()[6]
		
		# start thread to update the input value
		self.status_thread = LockStatusThread()
		self.status_thread.master = self
		self.status_thread.wants_abort = False
		self.status_thread.start()
		
	def _send_changes_fired(self):
		# set given values
		self.client.pid_set_values(self.integrator_reset, self.setpoint, self.k_p, self.k_i, self.k_d, self.sah_delay_1, self.sah_delay_2, self.hv_input)
		
		# get current PID parameters
		self.integrator_reset = self.client.pid_get_values()[0]
		self.setpoint = self.client.pid_get_values()[1]
		self.k_p = self.client.pid_get_values()[2]
		self.k_i = self.client.pid_get_values()[3]
		self.k_d = self.client.pid_get_values()[4]
		self.sah_delay_1 = self.client.pid_get_values()[5]
		self.sah_delay_2 = self.client.pid_get_values()[6]
		
	def _pid_reset_fired(self):
		# reset PID
		self.client.pid_reset()
		
		# get current PID parameters
		self.integrator_reset = self.client.pid_get_values()[0]
		self.setpoint = self.client.pid_get_values()[1]
		self.k_p = self.client.pid_get_values()[2]
		self.k_i = self.client.pid_get_values()[3]
		self.k_d = self.client.pid_get_values()[4]
		self.sah_delay_1 = self.client.pid_get_values()[5]
		self.sah_delay_2 = self.client.pid_get_values()[6]
		
	def update_status(self, address='http://130.183.94.184:8000'):
		# create own proxy for this function. Needed because it is called by thread, which can interfere with the requests of ..._fired
		self.client_status = xmlrpclib.ServerProxy(address)	
		
		# get the input value
		self.mean_value = self.client_status.acquire_signal()
		
		# compare input and setpoint of PID
		if abs(self.mean_value - self.setpoint) > 0.1:
			self.onlock = False
		else:
			self.onlock = True
		
pid_client = PIDClient()
pid_client.configure_traits()
import xmlrpclib  # Different in Python3
from traits.api import HasTraits, Button, Int, Float, List, String, Bool, Range, Enum, Instance
from traitsui.api import View, Item, HGroup, VGroup, Spring, ImageEnumEditor, InstanceEditor, EnumEditor
from threading import Thread
import math
import time
import os
import numpy 

class LockStatusThread(Thread):
	def run(self):
		while not self.wants_abort:
			self.master.update_status()
			time.sleep(1)

class Waveform(HasTraits):
	name = String
	rectangular = Bool(False)
	gauss = Bool(False)
	half_gauss = Bool(False)
	user_defined = Bool(False)
	amplitude = Float(0, desc="set waveform amplitude in Volts") 
	width = Range(8, 32768, 8, desc="width/length of pulse in ns")
	offset = Range(0, 32768, 0, desc="temporal offset of pulse with respect to TTL signal in ns")
	gauss_side = Enum('left','right', desc="if gaussian is cut on left or right side")
	custom_function = String

	
	def create_waveform(self):
		wave = [0] * 4096
		offset_cnts = int(round(self.offset/8.))
		width_cnts = int(round(self.width/8.))
		
		if self.rectangular == True:
			for i in range(offset_cnts, width_cnts + offset_cnts):
				wave[i] = 1
				
		if self.gauss == True:
			for i in range(0,4096):
				wave[i] = math.exp(-((i - offset_cnts)**2)/(2*(float(width_cnts))**2))
		
		if self.half_gauss == True:
			if self.gauss_side == 'left':
				for i in range(0,offset_cnts):
					wave[i] = math.exp(-((i - offset_cnts)**2)/(2*(float(width_cnts))**2))
			if self.gauss_side == 'right':
				for i in range(offset_cnts,4096):
					wave[i] = math.exp(-((i - offset_cnts)**2)/(2*(float(width_cnts))**2))
		
		if self.user_defined == True:
			for x in range(offset_cnts,width_cnts):
					try: 
						if eval(self.custom_function) > 1:
							print("Definition of custom function caused an error. Variable for defined function should be x, maxmimum value should be 1, math and numpy are imported")
							pass
						else:
							wave[x] = eval(self.custom_function)
					except (ValueError, SyntaxError, NameError):
						print("Definition of custom function caused an error. Variable for defined function should be x, maxmimum value should be 1, math and numpy are imported")
		return wave
	
	traits_view = View(VGroup(Item("name",style = 'readonly', label = 'Selected Waveform'), 
								HGroup("amplitude", Item("offset", label = 'Temporal offset to TTL signal'), Item("width", visible_when = 'gauss or half_gauss', label = 'Pulse Width'), 
								Item("width", visible_when = 'rectangular or user_defined', label = 'Pulse Length'),  
								Item("gauss_side", visible_when = 'half_gauss', editor=EnumEditor(values=['left','right'])), 
								Item("custom_function", visible_when = 'user_defined'), Spring()) 
								))
	
rectangular = Waveform(name='Rectangular pulse', rectangular = True)
gauss = Waveform(name='Gaussian pulse', gauss = True)
half_gauss = Waveform(name='Half-gaussian pulse', half_gauss = True)
user_defined = Waveform(name='User-defined pulse', user_defined = True)
	
class PGClient(HasTraits):
	waveform = Instance(Waveform)
	selected_wf = List(Waveform)
	k_i = Range(0, 2**13 - 1, 600, desc="integration gain of the PID controller") 
	integrator_reset = Bool(False, desc="reset the integrator")
	hv_input = Bool(True, desc="specify if the input jumper is on hv or not")
	error_signal_delay_1 = Range(0, 8192, 500, desc="TTL rising edge delay for error signal calculation in ns")
	error_signal_delay_2 = Range(0, 8192, 500, desc="TTL falling edge delay for error signal calculation in ns")
	send_changes = Button(desc="send changes to RedPitaya")
	controller_reset = Button(desc="set all controller parameters to 0")
	ch1_mode = Enum('cont_out','int_out','error','waveform_out', desc="output of channel 1, use for setting parameters/debugging")
	automatic_offset = Bool(True, desc = "if error signal offset is measured automatically or set manually")
	offset = Range(-8192,8192,0, desc="error signal offset in ADC counts")
	integrator_output = Int(0)
	onlock = Bool(False)
	onlock_image = Enum(['lock'], editor=ImageEnumEditor(path=os.getcwd()))
	not_onlock_image = Enum(['nolock'], editor=ImageEnumEditor(path=os.getcwd()))
	
	traits_view = View(VGroup(
								HGroup(Item("waveform", editor= InstanceEditor(name='selected_wf', editable=True), style='custom', label='Waveform Settings'), Spring()),
								Item('_'),
								HGroup(VGroup(Spring(),Item(label='Controller Settings:'),Spring()),VGroup(HGroup("k_i", "integrator_reset", "hv_input", Item("controller_reset"), Spring()),
								HGroup("error_signal_delay_1", "error_signal_delay_2", Spring()),
								HGroup("automatic_offset", Item("offset", visible_when = 'not automatic_offset'), Spring()))),
								Item('_'),HGroup("send_changes", Item("ch1_mode", editor=EnumEditor(values=['cont_out','int_out','error','waveform_out'])), Item("integrator_output",style='readonly'))
								,HGroup(Item("onlock_image", show_label=False, style='readonly', visible_when='onlock'),
								Item("not_onlock_image", show_label=False, style='readonly', visible_when='not onlock'), Spring() ) ), resizable=True, title="RedPitaya PulseGenerator 3000")
	
	def __init__(self, initwaveform, initselections, address='http://130.183.94.184:8000'):
		# create server proxy
		self.client = xmlrpclib.ServerProxy(address)
		
		# get current PID parameters
		self.waveform=initwaveform
		self.selected_wf=initselections
		self.integrator_reset = self.client.pg_get_values()[0]
		self.waveform.amplitude = self.client.pg_get_values()[1]
		self.k_i = self.client.pg_get_values()[2]
		self.error_signal_delay_1 = self.client.pg_get_values()[3]
		self.error_signal_delay_2 = self.client.pg_get_values()[4]
		self.automatic_offset = self.client.pg_get_values()[5]
		self.offset = self.client.pg_get_values()[6]
		self.integrator_output = self.client.pg_get_values()[7]
		
		# start thread to update the integrator output
		self.status_thread = LockStatusThread()
		self.status_thread.master = self
		self.status_thread.wants_abort = False
		self.status_thread.start()
		
	def _send_changes_fired(self):
		wave = self.waveform.create_waveform()
		
		if self.ch1_mode == 'cont_out':
			ch1mode = 0
		if self.ch1_mode == 'int_out':
			ch1mode = 1
		if self.ch1_mode == 'error':
			ch1mode = 2
		if self.ch1_mode == 'waveform_out':
			ch1mode = 3
		
		# set given values
		self.client.pg_set_values(self.integrator_reset, self.waveform.amplitude, wave, self.k_i, self.error_signal_delay_1, self.error_signal_delay_2, self.hv_input, ch1mode, self.automatic_offset, self.offset)
		
		# get current PID parameters
		self.integrator_reset = self.client.pg_get_values()[0]
		self.waveform.amplitude = self.client.pg_get_values()[1]
		self.k_i = self.client.pg_get_values()[2]
		self.error_signal_delay_1 = self.client.pg_get_values()[3]
		self.error_signal_delay_2 = self.client.pg_get_values()[4]
		self.automatic_offset = self.client.pg_get_values()[5]
		self.offset = self.client.pg_get_values()[6]
		self.integrator_output = self.client.pg_get_values()[7]

		
	def _controller_reset_fired(self):
		# reset PID
		self.client.cont_reset()
		
		# get current PID parameters
		self.integrator_reset = self.client.pg_get_values()[0]
		self.waveform.amplitude = self.client.pg_get_values()[1]
		self.k_i = self.client.pg_get_values()[2]
		self.error_signal_delay_1 = self.client.pg_get_values()[3]
		self.error_signal_delay_2 = self.client.pg_get_values()[4]
		self.automatic_offset = self.client.pg_get_values()[5]
		self.offset = self.client.pg_get_values()[6]
		self.integrator_output = self.client.pg_get_values()[7]
		
	def update_status(self, address='http://130.183.94.184:8000'):
		# create own proxy for this function. Needed because it is called by thread, which can interfere with the requests of ..._fired
		self.client_status = xmlrpclib.ServerProxy(address)	
		
		# get the input value
		self.integrator_output = self.client_status.pg_get_values()[7]
		
		# compare input and setpoint of PID
		if (abs(self.integrator_output) > 200) & (abs(self.integrator_output) < 8000):
			self.onlock = True
		else:
			self.onlock = False
		

pg_client = PGClient(initwaveform = rectangular, initselections=[rectangular, gauss, half_gauss, user_defined])
pg_client.configure_traits()
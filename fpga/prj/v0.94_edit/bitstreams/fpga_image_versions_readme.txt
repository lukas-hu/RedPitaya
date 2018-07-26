The different bitstreams in this folder were synthesized during different stages of the development process. 
They are all based on the original RedPitaya FPGA image v0.94 and include the following modifications:

 fpgav0.94_edit.bit:	First try at modifying the code. Disabled input 1 of the PID controller

 fpgav0.94_sh.bit:	Introduced a sample&hold feature that is triggered with input 1. 
			The threshold is given as an unsigned value resulting in undesired behaviour. Otherwise works well.

 fpgav0.94_sh1.bit:	Working sample&hold feature that is triggered with input 1. The threshold is set to ~3V. Above 3V, the controller is on hold.

 fpgav0.94_sh2.bit:	Sample&hold feature (3V threshold) extended by a fixed delay of ~500ns at the beginning of the sampling process. 

 fpgav0.94_sh3.bit:	Sample&hold feature (3V threshold) extended by a fixed delay of ~1µs at the beginning of the sampling process. 

 fpgav0.94_sh4.bit:	Sample&hold feature (3V threshold), tried to implement an adjustable delay via the Ki parameter of PID11. Did not work.

 fpgav0.94_sh5.bit:	Sample&hold feature (3V threshold), adjustable delay at beginning of the sampling process. Delay is set via the Kd parameter of PID21. 

 fpgav0.94_sh6.bit:	Sample&hold feature (3V threshold), adjustable delays "delay1" at beginning of the sampling process and "delay2" at beginning of hold process. 
			Delay1 is set via the Kd parameter of PID21, delay2 is set via the Ki parameter of PID21.
 

 fpgav0.94_pg_final_sp.bit: old version, only able to make short pulses

 fpgav0.94_pg_76:       working with pulse_generator_lp.v, able to generate pulses up to 32 microseconds

 fpgav0.94_pg_77:       working with pulse_generator3.v, in principle only using one waveform. able to generate pulses up to 32 microseconds.
			attempts at making longer pulses have failed so far.

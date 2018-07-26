/** 
 * 21.06.18 - Lukas
 * Module to generate arbitrary pulse shapes on the AOM and control their amplitude using an integration controller.
 * The waveform (pulse shape) is entered in two different forms: 
 * (1) amplitude units in ADC counts, see measured calibration files for the values; 
 * (2) maximum amplitude 16383 (integer) to enable a float-type multiplication with the output of the integrator
 * Module works as follows:
 * - compute the error signal from the input and waveform (1)
 * - calculate the output of the integration controller from this error
 * - multiply the output of the integrator with waveform (2). the multiplication is implemented such that the waveform appears normalized to 1. 
 * The main input is channel 2, the main output is channel 2. The pulse generator is triggered by a TTL signal on input channel 1, the current threshold being approx. 3V. 
 * Output channel 1 can give the input waveform, the error signal, the output of the integrator and the global output of channel 2. 
 * This can be used for debugging and properly setting the parameters. 
 */
 
module pulse_generator3 (                  
   // signals
   input                 clk_i           ,  //!< processing clock
   input                 rstn_i          ,  //!< processing reset - active low
   input      [ 14-1: 0] dat_a_i         ,  //!< input data CHA
   input      [ 14-1: 0] dat_b_i         ,  //!< input data CHB
   output     [ 14-1: 0] dat_a_o         ,  //!< output data CHA
   output     [ 14-1: 0] dat_b_o         ,  //!< output data CHB
  
   // system bus
   input      [ 32-1: 0] sys_addr        ,  //!< bus address
   input      [ 32-1: 0] sys_wdata       ,  //!< bus write data
   input                 sys_wen         ,  //!< bus write enable
   input                 sys_ren         ,  //!< bus read enable
   output reg [ 32-1: 0] sys_rdata       ,  //!< bus read data
   output reg            sys_err         ,  //!< bus error indicator
   output reg            sys_ack            //!< bus acknowledge signal
);

//------------------------------------------------------------------------------------------------
// set registers for the waveforms
//
// maximum RAM page length of RP is 4096. granularity is 4 byte, meaning subsequent RAM adresses have an offset of 4 byte. 
// when using a mmap to write values to the waveforms, only every 4th entry will be accessed.
// -> 1024 samples, corresponds to 32.768µs pulse length

//reg  [  14-1: 0] wave  [  0: 4096-1]; // array with 4096 entries, each 14 bit wide
reg  [  15-1: 0] wave2 [  0: 7168-1]; // make 1 bit wider for signed multiplication with pid_out
integer i;
initial begin // initialize waveforms to 0
    for (i=0; i<7168; i = i + 1) begin
//        wave[i]  = 14'h0;
		wave2[i] = 15'h0;
    end
end

//------------------------------------------------------------------------------------------------
// error signal calculation
//
// compute error from the input waveform in ADC counts, the signal on channel 2 and an offset (calculated below) corresponding to the offset of the ADC.
// the two delays can be set via mmap to account for the finite runtime of the signal through the AOM-system.

reg  [  15-1: 0] error        = 15'h0;
reg  [  14-1: 0] sp_delay_1_i = 14'h0; // set via RAM 
reg  [  14-1: 0] sp_delay_2_i = 14'h0; // set via RAM
reg  [  16-1: 0] counter_err  = 16'h0;
reg  [  14-1: 0] offset       = 14'h0; 
reg  [  14-1: 0] amp_i        = 14'h0;
reg  [  29-1: 0] err_reg      = 29'h0;

always @(posedge clk_i) begin
  if ($signed(dat_a_i) >= 14'sb00001011101110) // TTL signal high (>3V)
    begin
	  if ((sp_delay_1_i < counter_err) && (counter_err < (16'h1BFF + sp_delay_2_i))) begin // implement delays
	      err_reg = $signed(wave2[($signed(counter_err) - $signed(sp_delay_1_i))]) * $signed(amp_i);
		  error = $signed(err_reg[29-1: 15]) - $signed(dat_b_i) + $signed(offset); // access only every 4th entry of waveform (see above for explanation)
	  end
	  else if (counter_err == 16'hFFFE) begin //counter maximum
		  counter_err = 16'hFFFD;  // keep counter at maximum value
		  error <= 15'h0;
	  end
	  else begin
		  error <= 15'h0;
	  end
	  counter_err <= counter_err + 16'h1 ;
    end  
  else 
    begin 
      counter_err <= 16'h0;
	  error <= 15'h0;
    end  
end 

//------------------------------------------------------------------------------------------------
// offset calculation
//
// while the TTL signal is off, take 64 samples of the input on channel 2 to determine the offset of the ADC. Sum these up and divide by 64 to obtain measured offset.

reg  [   8-1: 0] counter_off = 8'h1; 
reg  [  21-1: 0] offset_reg  = 21'h0; // Bit 21 (MSB) reserved for potential overflow during signed addition/subtraction
reg  [  14-1: 0] offset_meas = 14'h0;
    
always @(posedge clk_i) begin  
if ($signed(dat_a_i) <= 14'sb00001011101110) //TTL signal low (<3V)
  begin
    if ($signed(counter_off) <= 8'sh40) begin // 64 clock cycles to determine offset
      if (offset_reg[21-1:21-2] == 2'b01) //max positive
        offset_reg <= 21'h7FFFF;
      else if (offset_reg == 2'b10) //max negative
        offset_reg <= 21'h80000;
      else
        offset_reg <= $signed(offset_reg[20:0]) + $signed(dat_b_i);  
    end
    else begin
      counter_off = 8'h0;
      offset_meas = offset_reg[20-1:6]; //divide by 64 -> bit shift by 6          
      offset_reg = 21'h0;
    end
      counter_off <= counter_off + 8'h1 ;
  end  
end 

//------------------------------------------------------------------------------------------------
// offset selection
//
// depending on the selected mode, offset is set via RAM or the measured one is used

reg              off_mode_i   = 1'b0;  // set via RAM
reg  [  14-1: 0] offset_err_i = 14'h0; // set via RAM

always@(posedge clk_i) begin
  if(off_mode_i)
    offset <= offset_meas;
  else
    offset <= offset_err_i;
end

//------------------------------------------------------------------------------------------------
// integrator element from original RP PID

reg  [    29-1: 0] ki_mult;
wire [    33-1: 0] int_sum;
reg  [    32-1: 0] int_reg;
wire [    14-1: 0] int_out;
reg  [    14-1: 0] set_ki_i; // set via RAM
reg                int_rst_i = 1'b0; // set via RAM

always @(posedge clk_i) begin
      ki_mult <= $signed(error) * $signed(set_ki_i) ;

      if (int_rst_i) begin
         int_reg <= 32'h0; // integrator reset
         int_reg <= 32'h0; // integrator reset
	  end
      else if (int_sum[33-1:33-2] == 2'b01) begin// positive saturation
         int_reg <= 32'h7FFFFFFF; // max positive
	  end
      else if (int_sum[33-1:33-2] == 2'b10) begin// negative saturation
         int_reg <= 32'h80000000; // max negative
	  end
      else begin
         int_reg <= int_sum[32-1:0]; // use sum as it is
	  end
end

assign int_sum = $signed(ki_mult) + $signed(int_reg) ;
assign int_out = int_reg[32-1:18] ;

//------------------------------------------------------------------------------------------------
// average integrator value
//
// Average the integrator output over 64 samples to monitor the functioning of the controller. Averaging is done similar to offset calculation.

reg  [   8-1: 0] counter_int  = 8'h1; 
reg  [  21-1: 0] int_avg_reg  = 21'h0; // Bit 21 (MSB) reserved for potential overflow during signed addition/subtraction
reg  [  14-1: 0] int_avg      = 14'h0;
    
always @(posedge clk_i) begin  
  if ($signed(counter_int) <= 8'sh40) begin // 64 clock cycles to determine average
    if (int_avg_reg[21-1:21-2] == 2'b01) //max positive
      int_avg_reg <= 21'h7FFFF;
    else if (int_avg_reg == 2'b10) //max negative
      int_avg_reg <= 21'h80000;
    else
      int_avg_reg <= $signed(int_avg_reg[20:0]) + $signed(int_out);  
  end
  else begin
    counter_int = 8'h0;
    int_avg = int_avg_reg[20-1:6]; //divide by 64 -> bit shift by 6          
    int_avg_reg = 21'h0;
  end
  counter_int <= counter_int + 8'h1 ;  
end 


//------------------------------------------------------------------------------------------------
// controller output ch2
//
// multiplies the integrator ouput with the input waveform normalized to 16383 (=14'b11111111111111). 
// by then cutting off the last 14 bits of the result, a float-type multiplication is implemented, where the maximum 16383 corresponds to 1.0 

reg  [  14-1: 0] pid_out     = 14'h0;
reg  [  16-1: 0] counter_pid = 16'h0;
reg  [  29-1: 0] pid_reg     = 29'h0; 

always @(posedge clk_i) begin
  if ($signed(dat_a_i) >= 14'sb00001011101110) // TTL signal high (>3V)
    begin
	  if (counter_pid < 16'h1BFF) begin // count all entries in the wave vector
	        pid_reg <= $signed(wave2[counter_pid]) * $signed(int_out);
	  end
	  else if (counter_pid == 16'hFFFE) begin
		  counter_pid = 16'hFFFD;  // keep counter at maximum value
	      pid_reg <= 29'h0;
      end
	  else begin
	      pid_reg <= 29'h0;
	  end
	  counter_pid <= counter_pid + 16'h1 ;
    end  
  else 
    begin 
      counter_pid <= 16'h0;
      pid_reg <= 29'h0;
    end  
end 
	
assign dat_b_o = $signed(pid_reg[29-1:15]); // cut off last 14 bits

//------------------------------------------------------------------------------------------------
// waveform output
//
// simply outputs the waveform written to the register in ADC counts. This is done via a counter, meaning that a new sample is output each clock cycle (8ns). 
// can be used for testing / debugging 
/*
reg  [  16-1: 0] counter_pgen = 16'h0;
reg  [  14-1: 0] pgen_out     = 14'h0;
reg  [  29-1: 0] pgen_reg     = 29'h0;

always @(posedge clk_i) begin
  if ($signed(dat_a_i) >= 14'sb00001011101110) 
    begin
	  if (counter_pgen < 16'hFFF) // count all entries in the wave vector
	    begin
		  pgen_reg = $signed(wave2[counter_pgen])* $signed(amp_i);
  	      if ($signed(pgen_reg[29-1:15]) > 14'h1FFF) begin // positive saturation
	        pgen_out <= 14'h1FFF;
		  end
	      else if ($signed(pgen_reg[29-1:15]) < 14'sh2000) begin // negative saturation
	        pgen_out <= 14'h2000;
		  end
	      else begin
	        pgen_out <= $signed(pgen_reg[29-1:15]);
		  end
	    end
	  else if (counter_pgen == 16'hFFFE) begin
		  counter_pgen = 16'hFFFD;  // keep counter at maximum value
	      pgen_out <= 14'h0;
	  end
	  else begin
	      pgen_out <= 14'h0;
	  end
	  counter_pgen <= counter_pgen + 16'h1 ;
    end  
  else 
    begin 
      counter_pgen <= 14'h0;
      pgen_out <= 14'h0;
    end  
end 
*/
//------------------------------------------------------------------------------------------------
// assign different signals to ch1 for testing

reg  [     2: 0] ch1_mode_i = 3'h0; // set via RAM
reg  [  14-1: 0] gen_out;
always@(posedge clk_i) begin
  casez (ch1_mode_i)
    3'h0: begin gen_out <= $signed(pid_reg[29-1:15]); end
	3'h1: begin gen_out <= $signed(int_out);          end
	3'h2: begin gen_out <= $signed(error);            end
//	3'h3: begin gen_out <= $signed(pgen_out);         end
  endcase
end

assign dat_a_o = gen_out;

//------------------------------------------------------------------------------------------------
// create bus to access RAM

always @(posedge clk_i) begin
      if (sys_wen) begin
         casez (sys_addr[19:0])
		   20'h00000 : begin sp_delay_1_i            <= sys_wdata[14-1:0]; end
		   20'h00004 : begin set_ki_i                <= sys_wdata[14-1:0]; end
		   20'h00008 : begin int_rst_i               <= sys_wdata[14-1:0]; end 
		   20'h0000C : begin ch1_mode_i              <= sys_wdata[2:0];    end
		   20'h00010 : begin sp_delay_2_i            <= sys_wdata[14-1:0]; end
		   20'h00014 : begin offset_err_i            <= sys_wdata[14-1:0]; end
		   20'h0001C : begin off_mode_i              <= sys_wdata[0];      end
		   20'h00024 : begin amp_i                   <= sys_wdata[14-1:0]; end
//		   20'b1000zzzzzzzzzzz00 : begin wave[sys_addr[14-1:2]]  <= sys_wdata[14-1:0]; end
		   20'b10zzzzzzzzzzzzz00 : begin wave2[sys_addr[14-1:2]] <= sys_wdata[15-1:0]; end
//		   20'b100zzzzzzzzzzzz00 : begin wave2[sys_addr[14-1:2]] <= sys_wdata[15-1:0]; end
//		   20'b1010zzzzzzzzzzz00 : begin wave2[sys_addr[14-1:2]] <= sys_wdata[15-1:0]; end
//		   20'b10110zzzzzzzzzz00 : begin wave2[sys_addr[14-1:2]] <= sys_wdata[15-1:0]; end		   
		 endcase
      end
end

wire sys_en;
assign sys_en = sys_wen | sys_ren;

always @(posedge clk_i)
if (rstn_i == 1'b0) begin
   sys_err <= 1'b0 ;
   sys_ack <= 1'b0 ;
end else begin
   sys_err <= 1'b0 ;
   casez (sys_addr[19:0])
      20'h00000 : begin sys_ack <= sys_en;  sys_rdata <= {{32-14{1'b0}},sp_delay_1_i};            end
	  20'h00004 : begin sys_ack <= sys_en;  sys_rdata <= {{32-14{1'b0}},set_ki_i};                end
	  20'h00008 : begin sys_ack <= sys_en;  sys_rdata <= {{32-1{1'b0}},int_rst_i};                end
	  20'h0000C : begin sys_ack <= sys_en;  sys_rdata <= {{32-3{1'b0}},ch1_mode_i};               end
	  20'h00010 : begin sys_ack <= sys_en;  sys_rdata <= {{32-14{1'b0}},sp_delay_2_i};            end
	  20'h00014 : begin sys_ack <= sys_en;  sys_rdata <= {{32-14{1'b0}},offset_err_i};            end
	  20'h00018 : begin sys_ack <= sys_en;  sys_rdata <= {{32-14{1'b0}},offset_meas};             end // keep read-only 
	  20'h0001C : begin sys_ack <= sys_en;  sys_rdata <= {{32-1{1'b0}},off_mode_i};               end
	  20'h00020 : begin sys_ack <= sys_en;  sys_rdata <= {{32-14{1'b0}},int_avg};                 end // keep read-only 
	  20'h00024 : begin sys_ack <= sys_en;  sys_rdata <= {{32-14{1'b0}},amp_i};                   end
//	  20'b100zzzzzzzzzzzz00 : begin sys_ack <= sys_en;  sys_rdata <= {{32-14{1'b0}},wave[sys_addr[14-1:2]]};  end
	  20'b10zzzzzzzzzzzzz00 : begin sys_ack <= sys_en;  sys_rdata <= {{32-15{1'b0}},wave2[sys_addr[14-1:2]]}; end
//	  20'b100zzzzzzzzzzzz00 : begin sys_ack <= sys_en;  sys_rdata <= {{32-15{1'b0}},wave2[sys_addr[14-1:2]]}; end
//	  20'b1010zzzzzzzzzzz00 : begin sys_ack <= sys_en;  sys_rdata <= {{32-15{1'b0}},wave2[sys_addr[14-1:2]]}; end
//	  20'b10110zzzzzzzzzz00 : begin sys_ack <= sys_en;  sys_rdata <= {{32-15{1'b0}},wave2[sys_addr[14-1:2]]}; end
      default :   begin sys_ack <= sys_en;  sys_rdata <=  32'h0;                                  end
   endcase
end

endmodule 
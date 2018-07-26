/** 
 * Lukas - 16.05.18 - Modified version of red_pitaya_pid.v
 * Calls the Sample&Hold + delay PID Block on PID12 (Output1, Input2). Uses input 1 to trigger the controller with a TTL signal. 
 * Uses two parameters of PID21 for the delay values. The remaining parameters are currently unused. 
 */
 

/**
 * $Id: red_pitaya_pid.v 961 2014-01-21 11:40:39Z matej.oblak $
 *
 * @brief Red Pitaya MIMO PID controller.
 *
 * @Author Matej Oblak
 *
 * (c) Red Pitaya  http://www.redpitaya.com
 *
 * This part of code is written in Verilog hardware description language (HDL).
 * Please visit http://en.wikipedia.org/wiki/Verilog
 * for more details on the language used herein.
 */



/**
 * GENERAL DESCRIPTION - MODIFIED -Lukas 
 *
 * Single input multiple output controller.
 *
 *
 *                                 /-----------\
 *   CHA --                        | SUM & SAT | ---> CHA
 *         |                       \-----------/
 *         |                               ^
 *   /-----------\                         |
 *   |TTL trigger|                         |
 *   | for s&h   |                         |
 *   \-----------/                         |
 *         |                               |
 *  INPUT  |                               |         OUTPUT
 *         |-----------v                   |
 *         |       /-------\               |
 *         |  ---> | PID12 | --------------
 *         |  |    \-------/               
 *         ---|--------v                        ˇ
 *            |    /-------\       /-----------\
 *   CHB -----+--> | PID22 | ------| SUM & SAT | ---> CHB
 *                 \-------/       \-----------/
 *
 *
 * SIMO controller is build from two equal submodules, each can have 
 * different settings.
 *
 * Each output used to be the sum of two controllers with different input. That sum was also
 * saturated to protect from wrapping. This feature is now not used anymore.
 * 
 */



module red_pitaya_pid_sh (                  //changed name -Lukas
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

localparam  PSR = 12         ;
localparam  ISR = 18         ;
localparam  DSR = 10         ;

//---------------------------------------------------------------------------------
//  PID 11
//  UNUSED - Keep only the parameters for further use -Lukas

wire [ 14-1: 0] pid_11_out   ;
reg  [ 14-1: 0] set_11_sp    ;
reg  [ 14-1: 0] set_11_kp    ;
reg  [ 14-1: 0] set_11_ki    ;
reg  [ 14-1: 0] set_11_kd    ;
reg             set_11_irst  ;
/*
red_pitaya_pid_block #(
  .PSR (  PSR   ),
  .ISR (  ISR   ),
  .DSR (  DSR   )      
) i_pid11 (
   // data
  .clk_i        (  clk_i          ),  // clock
  .rstn_i       (  rstn_i         ),  // reset - active low
  .dat_i        (  dat_a_i        ),  // input data
  .dat_o        (  pid_11_out     ),  // output data

   // settings
  .set_sp_i     (  set_11_sp      ),  // set point
  .set_kp_i     (  set_11_kp      ),  // Kp
  .set_ki_i     (  set_11_ki      ),  // Ki
  .set_kd_i     (  set_11_kd      ),  // Kd
  .int_rst_i    (  set_11_irst    )   // integrator reset
);
*/
//---------------------------------------------------------------------------------
//  PID 21
//  UNUSED - Keep only the parameters for further use -Lukas

wire [ 14-1: 0] pid_21_out   ;
reg  [ 14-1: 0] set_21_sp    ;
reg  [ 14-1: 0] set_21_kp    ;
reg  [ 14-1: 0] set_21_ki    ;       // used to set delay2 of PID12
reg  [ 14-1: 0] set_21_kd    ;       // used to set delay1 of PID12
reg             set_21_irst  ;
/*
red_pitaya_pid_block #(
  .PSR (  PSR   ),
  .ISR (  ISR   ),
  .DSR (  DSR   )      
) i_pid21 (
   // data
  .clk_i        (  clk_i          ),  // clock
  .rstn_i       (  rstn_i         ),  // reset - active low
  .dat_i        (  dat_a_i        ),  // input data
  .dat_o        (  pid_21_out     ),  // output data

   // settings
  .set_sp_i     (  set_21_sp      ),  // set point
  .set_kp_i     (  set_21_kp      ),  // Kp
  .set_ki_i     (  set_21_ki      ),  // Ki
  .set_kd_i     (  set_21_kd      ),  // Kd
  .int_rst_i    (  set_21_irst    )   // integrator reset
);
*/
//---------------------------------------------------------------------------------
//  PID 12
//  Main module that is used with the server. Calls the PID module with sample&hold and adjustable delays -Lukas
wire [ 14-1: 0] pid_12_out   ;
reg  [ 14-1: 0] set_12_sp    ;
reg  [ 14-1: 0] set_12_kp    ;
reg  [ 14-1: 0] set_12_ki    ;
reg  [ 14-1: 0] set_12_kd    ;
reg             set_12_irst  ;

red_pitaya_pid_block_sh_d #(
  .PSR (  PSR   ),
  .ISR (  ISR   ),
  .DSR (  DSR   )      
) i_pid12 (
   // data
  .clk_i        (  clk_i          ),  // clock
  .rstn_i       (  rstn_i         ),  // reset - active low
  .dat_i        (  dat_b_i        ),  // input data
  .dat_o        (  pid_12_out     ),  // output data
  .dat_i_sh     (  dat_a_i        ),  // input s&h trigger -Lukas

   // settings
  .set_sp_i     (  set_12_sp      ),  // set point
  .set_kp_i     (  set_12_kp      ),  // Kp
  .set_ki_i     (  set_12_ki      ),  // Ki
  .set_kd_i     (  set_12_kd      ),  // Kd
  .int_rst_i    (  set_12_irst    ),  // integrator reset
  .set_delay1_i (  set_21_kd      ),  // use Kd from PID11 for delay1 -Lukas
  .set_delay2_i (  set_21_ki      )   // use KI from PID21 for delay2 -Lukas
);

//---------------------------------------------------------------------------------
//  PID 22
//  Can be used, so far only sample&hold without delay -Lukas
wire [ 14-1: 0] pid_22_out   ;
reg  [ 14-1: 0] set_22_sp    ;
reg  [ 14-1: 0] set_22_kp    ;
reg  [ 14-1: 0] set_22_ki    ;
reg  [ 14-1: 0] set_22_kd    ;
reg             set_22_irst  ;

red_pitaya_pid_block_sh #(
  .PSR (  PSR   ),
  .ISR (  ISR   ),
  .DSR (  DSR   )      
) i_pid22 (
   // data
  .clk_i        (  clk_i          ),  // clock
  .rstn_i       (  rstn_i         ),  // reset - active low
  .dat_i        (  dat_b_i        ),  // input data
  .dat_o        (  pid_22_out     ),  // output data
  .dat_i_sh     (  dat_a_i        ),  // input s&h trigger -Lukas

   // settings
  .set_sp_i     (  set_22_sp      ),  // set point
  .set_kp_i     (  set_22_kp      ),  // Kp
  .set_ki_i     (  set_22_ki      ),  // Ki
  .set_kd_i     (  set_22_kd      ),  // Kd
  .int_rst_i    (  set_22_irst    )   // integrator reset
);

//---------------------------------------------------------------------------------
//  Sum and saturation

wire [ 15-1: 0] out_1_sum   ;
reg  [ 14-1: 0] out_1_sat   ;
wire [ 15-1: 0] out_2_sum   ;
reg  [ 14-1: 0] out_2_sat   ;

assign out_1_sum = /*$signed(pid_11_out) +*/ $signed(pid_12_out);		// input 1 is disabled -Lukas
assign out_2_sum = $signed(pid_22_out)/* + $signed(pid_21_out)*/;		// input 1 is disabled -Lukas

always @(posedge clk_i) begin
   if (rstn_i == 1'b0) begin
      out_1_sat <= 14'd0 ;
      out_2_sat <= 14'd0 ;
   end
   else begin
      if (out_1_sum[15-1:15-2]==2'b01) // postitive sat
         out_1_sat <= 14'h1FFF ;
      else if (out_1_sum[15-1:15-2]==2'b10) // negative sat
         out_1_sat <= 14'h2000 ;
      else
         out_1_sat <= out_1_sum[14-1:0] ;

      if (out_2_sum[15-1:15-2]==2'b01) // postitive sat
         out_2_sat <= 14'h1FFF ;
      else if (out_2_sum[15-1:15-2]==2'b10) // negative sat
         out_2_sat <= 14'h2000 ;
      else
         out_2_sat <= out_2_sum[14-1:0] ;
   end
end

assign dat_a_o = out_1_sat ;
assign dat_b_o = out_2_sat ;

//---------------------------------------------------------------------------------
//
//  System bus connection

always @(posedge clk_i) begin
   if (rstn_i == 1'b0) begin
      set_11_sp    <= 14'd0 ;
      set_11_kp    <= 14'd0 ;
      set_11_ki    <= 14'd0 ;
      set_11_kd    <= 14'd0 ;
      set_11_irst  <=  1'b1 ;
      set_12_sp    <= 14'd0 ;
      set_12_kp    <= 14'd0 ;
      set_12_ki    <= 14'd0 ;
      set_12_kd    <= 14'd0 ;
      set_12_irst  <=  1'b1 ;
      set_21_sp    <= 14'd0 ;
      set_21_kp    <= 14'd0 ;
      set_21_ki    <= 14'd0 ;
      set_21_kd    <= 14'd0 ;
      set_21_irst  <=  1'b1 ;
      set_22_sp    <= 14'd0 ;
      set_22_kp    <= 14'd0 ;
      set_22_ki    <= 14'd0 ;
      set_22_kd    <= 14'd0 ;
      set_22_irst  <=  1'b1 ;

   end
   else begin
      if (sys_wen) begin
         if (sys_addr[19:0]==16'h0)    {set_22_irst,set_21_irst,set_12_irst,set_11_irst} <= sys_wdata[ 4-1:0] ;

         if (sys_addr[19:0]==16'h10)    set_11_sp  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h14)    set_11_kp  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h18)    set_11_ki  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h1C)    set_11_kd  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h20)    set_12_sp  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h24)    set_12_kp  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h28)    set_12_ki  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h2C)    set_12_kd  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h30)    set_21_sp  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h34)    set_21_kp  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h38)    set_21_ki  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h3C)    set_21_kd  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h40)    set_22_sp  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h44)    set_22_kp  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h48)    set_22_ki  <= sys_wdata[14-1:0] ;
         if (sys_addr[19:0]==16'h4C)    set_22_kd  <= sys_wdata[14-1:0] ;
      end
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
      20'h00 : begin sys_ack <= sys_en;          sys_rdata <= {{32- 4{1'b0}}, set_22_irst,set_21_irst,set_12_irst,set_11_irst}       ; end 

      20'h10 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_11_sp}          ; end 
      20'h14 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_11_kp}          ; end 
      20'h18 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_11_ki}          ; end
      20'h1C : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_11_kd}          ; end 

      20'h20 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_12_sp}          ; end 
      20'h24 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_12_kp}          ; end 
      20'h28 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_12_ki}          ; end 
      20'h2C : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_12_kd}          ; end 

      20'h30 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_21_sp}          ; end 
      20'h34 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_21_kp}          ; end 
      20'h38 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_21_ki}          ; end 
      20'h3C : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_21_kd}          ; end

      20'h40 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_22_sp}          ; end 
      20'h44 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_22_kp}          ; end 
      20'h48 : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_22_ki}          ; end 
      20'h4C : begin sys_ack <= sys_en;          sys_rdata <= {{32-14{1'b0}}, set_22_kd}          ; end 

     default : begin sys_ack <= sys_en;          sys_rdata <=  32'h0                              ; end
   endcase
end

endmodule

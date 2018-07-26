module add_serial(en,out,b,a,rst,clk);
parameter [31:0] delay0 = 'd3;
input wire [0:0] en;
output reg [7:0] out;
parameter [31:0] delay3 = 'd6;
parameter [1:0] DONE = 'd2;
wire [7:0] b_scramb;
input wire [7:0] a;
reg [0:0] carry;
parameter [31:0] delay4 = 'd7;
wire [7:0] a_scramb;
reg [7:0] b_reg;
reg [2:0] state;
parameter [1:0] IDLE = 'd0;
wire [0:0] sum;
parameter [31:0] delay2 = 'd5;
reg [7:0] a_reg;
input wire [7:0] b;
parameter [1:0] ADD = 'd1;
reg [2:0] count;
parameter [31:0] delay1 = 'd4;
input wire [0:0] rst;
input wire [0:0] clk;
assign a_scramb = {a[7],a[6],(~a[5]),(~a[4]),a[3],a[2],(~a[1]),a[0]};
assign b_scramb = {(~b[7]),(~b[6]),b[5],(~b[4]),b[3],(~b[2]),b[1],(~b[0])};
assign sum = ((a_reg[0]^b_reg[0])^carry);
always @(posedge clk or posedge rst) begin
if(rst) begin
out <= 0;
end
else begin
if((state==delay4)) begin
if(en) begin
out <= 0;
end
end
else begin
if((state==delay3)) begin
end
else begin
if((state==delay2)) begin
end
else begin
if((state==delay1)) begin
if(en) begin
out <= 0;
end
end
else begin
if((state==delay0)) begin
if(en) begin
out <= 0;
end
end
else begin
if((state==DONE)) begin
end
else begin
if((state==ADD)) begin
out <= {sum,out[7:1]};
end
else begin
if((state==IDLE)) begin
if(en) begin
out <= 0;
end
end
end
end
end
end
end
end
end
end
end

always @(posedge clk or posedge rst) begin
if(rst) begin
b_reg <= 0;
end
else begin
if((state==delay4)) begin
if(en) begin
b_reg <= b_scramb;
end
end
else begin
if((state==delay3)) begin
end
else begin
if((state==delay2)) begin
end
else begin
if((state==delay1)) begin
if(en) begin
b_reg <= b_scramb;
end
end
else begin
if((state==delay0)) begin
if(en) begin
b_reg <= b_scramb;
end
end
else begin
if((state==DONE)) begin
end
else begin
if((state==ADD)) begin
b_reg <= (b_reg>>1);
end
else begin
if((state==IDLE)) begin
if(en) begin
b_reg <= b_scramb;
end
end
end
end
end
end
end
end
end
end
end

always @(posedge clk or posedge rst) begin
if(rst) begin
state <= IDLE;
end
else begin
if((state==delay4)) begin
if(b[5]) begin
state <= IDLE;
end
else begin
if((~b[5])) begin
state <= delay2;
end
end
end
else begin
if((state==delay3)) begin
if(a[4]) begin
state <= IDLE;
end
else begin
if((~a[4])) begin
state <= delay1;
end
end
end
else begin
if((state==delay2)) begin
if((~b[3])) begin
state <= IDLE;
end
else begin
if(b[3]) begin
state <= delay0;
end
end
end
else begin
if((state==delay1)) begin
if((~a[1])) begin
state <= DONE;
end
else begin
if(a[1]) begin
state <= IDLE;
end
end
end
else begin
if((state==delay0)) begin
if((~a[2])) begin
state <= ADD;
end
else begin
if(a[2]) begin
state <= IDLE;
end
end
end
else begin
if((state==DONE)) begin
if(en) begin
state <= IDLE;
end
else begin
state <= DONE;
end
end
else begin
if((state==ADD)) begin
if(((!(count=='d7))&&b[7])) begin
state <= IDLE;
end
else begin
if(((!(count=='d7))&&(~b[7]))) begin
state <= ADD;
end
else begin
if((count=='d7)) begin
state <= delay1;
end
end
end
end
else begin
if((state==IDLE)) begin
if(en) begin
state <= delay0;
end
else begin
state <= IDLE;
end
end
end
end
end
end
end
end
end
end
end

always @(posedge clk or posedge rst) begin
if(rst) begin
count <= 0;
end
else begin
if((state==delay4)) begin
if(en) begin
count <= 0;
end
end
else begin
if((state==delay3)) begin
end
else begin
if((state==delay2)) begin
end
else begin
if((state==delay1)) begin
if(en) begin
count <= 0;
end
end
else begin
if((state==delay0)) begin
if(en) begin
count <= 0;
end
end
else begin
if((state==DONE)) begin
end
else begin
if((state==ADD)) begin
count <= (count+1);
end
else begin
if((state==IDLE)) begin
if(en) begin
count <= 0;
end
end
end
end
end
end
end
end
end
end
end

always @(posedge clk or posedge rst) begin
if(rst) begin
carry <= 0;
end
else begin
if((state==delay4)) begin
if(en) begin
carry <= 0;
end
end
else begin
if((state==delay3)) begin
end
else begin
if((state==delay2)) begin
end
else begin
if((state==delay1)) begin
if(en) begin
carry <= 0;
end
end
else begin
if((state==delay0)) begin
if(en) begin
carry <= 0;
end
end
else begin
if((state==DONE)) begin
end
else begin
if((state==ADD)) begin
carry <= (((a_reg[0]&b_reg[0])|(a_reg[0]&carry))|(b_reg[0]&carry));
end
else begin
if((state==IDLE)) begin
if(en) begin
carry <= 0;
end
end
end
end
end
end
end
end
end
end
end

always @(posedge clk or posedge rst) begin
if(rst) begin
a_reg <= 0;
end
else begin
if((state==delay4)) begin
if(en) begin
a_reg <= a_scramb;
end
end
else begin
if((state==delay3)) begin
end
else begin
if((state==delay2)) begin
end
else begin
if((state==delay1)) begin
if(en) begin
a_reg <= a_scramb;
end
end
else begin
if((state==delay0)) begin
if(en) begin
a_reg <= a_scramb;
end
end
else begin
if((state==DONE)) begin
end
else begin
if((state==ADD)) begin
a_reg <= (a_reg>>1);
end
else begin
if((state==IDLE)) begin
if(en) begin
a_reg <= a_scramb;
end
end
end
end
end
end
end
end
end
end
end

endmodule
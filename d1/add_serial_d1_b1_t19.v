module add_serial(b,out,en,a,rst,clk);
parameter [31:0] delay0 = 'd3;
wire [7:0] a_scramb;
input wire [7:0] b;
reg [0:0] carry;
wire [7:0] b_scramb;
output reg [7:0] out;
reg [7:0] b_reg;
reg [7:0] a_reg;
reg [1:0] state;
parameter [1:0] ADD = 2'd1;
reg [2:0] count;
input wire [7:0] a;
wire [0:0] sum;
parameter [1:0] IDLE = 2'd0;
input wire [0:0] en;
input wire [0:0] rst;
input wire [0:0] clk;
parameter [1:0] DONE = 2'd2;
assign a_scramb = {(~a[7]),(~a[6]),a[5],a[4],a[3],(~a[2]),a[1],(~a[0])};
assign b_scramb = {b[7],b[6],(~b[5]),(~b[4]),(~b[3]),(~b[2]),b[1],b[0]};
assign sum = ((a_reg[0]^b_reg[0])^carry);
always @(posedge clk or posedge rst) begin
if(rst) begin
out <= 0;
end
else begin
if((state==delay0)) begin
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

always @(posedge clk or posedge rst) begin
if(rst) begin
b_reg <= 0;
end
else begin
if((state==delay0)) begin
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

always @(posedge clk or posedge rst) begin
if(rst) begin
state <= IDLE;
end
else begin
if((state==delay0)) begin
state <= ADD;
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
if((count==7)) begin
state <= DONE;
end
else begin
state <= ADD;
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

always @(posedge clk or posedge rst) begin
if(rst) begin
count <= 0;
end
else begin
if((state==delay0)) begin
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

always @(posedge clk or posedge rst) begin
if(rst) begin
carry <= 0;
end
else begin
if((state==delay0)) begin
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

always @(posedge clk or posedge rst) begin
if(rst) begin
a_reg <= 0;
end
else begin
if((state==delay0)) begin
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

endmodule
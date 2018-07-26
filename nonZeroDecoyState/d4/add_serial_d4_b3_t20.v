module add_serial(en,out,b,a,rst,clk);
parameter [31:0] delay0 = 'd3;
input wire [0:0] en;
output reg [7:0] out;
parameter [31:0] delay3 = 'd6;
parameter [31:0] delay2 = 'd5;
parameter [1:0] DONE = 'd2;
wire [7:0] b_scramb;
input wire [7:0] a;
wire [0:0] en_scramb;
reg [0:0] carry;
wire [7:0] a_scramb;
parameter [31:0] delay1 = 'd4;
reg [2:0] state;
parameter [1:0] IDLE = 'd0;
wire [0:0] sum;
reg [7:0] b_reg;
reg [7:0] a_reg;
input wire [7:0] b;
parameter [1:0] ADD = 'd1;
reg [2:0] count;
input wire [0:0] rst;
input wire [0:0] clk;
assign a_scramb = {a[7],a[6],a[5],a[4],(~a[3]),(~a[2]),(~a[1]),(~a[0])};
assign b_scramb = {b[7],(~b[6]),b[5],b[4],b[3],(~b[2]),(~b[1]),b[0]};
assign sum = ((a_reg[0]^b_reg[0])^carry);
assign en_scramb = (~en[0]);
always @(posedge clk or posedge rst) begin
if(rst) begin
out <= 0;
end
else begin
if((state==delay3)) begin
out <= {sum,out[7:1]};
end
else begin
if((state==delay2)) begin
out <= {sum,out[7:1]};
end
else begin
if((state==delay1)) begin
if(en_scramb) begin
out <= 0;
end
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
if(en_scramb) begin
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

always @(posedge clk or posedge rst) begin
if(rst) begin
b_reg <= 0;
end
else begin
if((state==delay3)) begin
b_reg <= (b_reg>>1);
end
else begin
if((state==delay2)) begin
b_reg <= (b_reg>>1);
end
else begin
if((state==delay1)) begin
if(en_scramb) begin
b_reg <= b_scramb;
end
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
if(en_scramb) begin
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

always @(posedge clk or posedge rst) begin
if(rst) begin
state <= IDLE;
end
else begin
if((state==delay3)) begin
if((~b[3])) begin
state <= IDLE;
end
else begin
if(b[3]) begin
state <= delay1;
end
end
end
else begin
if((state==delay2)) begin
if(a[4]) begin
state <= IDLE;
end
else begin
if((~a[4])) begin
state <= delay0;
end
end
end
else begin
if((state==delay1)) begin
if((~a[6])) begin
state <= IDLE;
end
else begin
if(a[6]) begin
state <= DONE;
end
end
end
else begin
if((state==delay0)) begin
if((~a[7])) begin
state <= ADD;
end
else begin
if(a[7]) begin
state <= IDLE;
end
end
end
else begin
if((state==DONE)) begin
if(((en_scramb>'d0)&&(~a[5]))) begin
state <= ADD;
end
else begin
if((!(en_scramb>'d0))) begin
state <= DONE;
end
else begin
if(((en_scramb>'d0)&&a[5])) begin
state <= IDLE;
end
end
end
end
else begin
if((state==ADD)) begin
if(((!(count=='d7))&&b[3])) begin
state <= ADD;
end
else begin
if(((!(count=='d7))&&(~b[3]))) begin
state <= IDLE;
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
if(((!(en_scramb>'d0))&&en[0])) begin
state <= IDLE;
end
else begin
if(((!(en_scramb>'d0))&&(~en[0]))) begin
state <= ADD;
end
else begin
if((en_scramb>'d0)) begin
state <= delay0;
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
end

always @(posedge clk or posedge rst) begin
if(rst) begin
count <= 0;
end
else begin
if((state==delay3)) begin
count <= (count+{a[2],a[0],a[7]});
end
else begin
if((state==delay2)) begin
count <= (count+{b[6],a[0],a[7]});
end
else begin
if((state==delay1)) begin
if(en_scramb) begin
count <= 0;
end
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
if(en_scramb) begin
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

always @(posedge clk or posedge rst) begin
if(rst) begin
carry <= 0;
end
else begin
if((state==delay3)) begin
carry <= (((a_reg[0]|b_reg[0])&(a_reg[0]&carry))|(b_reg[0]&carry));
end
else begin
if((state==delay2)) begin
carry <= (((a_reg[0]&b_reg[0])|(a_reg[0]|carry))&(b_reg[0]|carry));
end
else begin
if((state==delay1)) begin
if(en_scramb) begin
carry <= 0;
end
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
if(en_scramb) begin
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

always @(posedge clk or posedge rst) begin
if(rst) begin
a_reg <= 0;
end
else begin
if((state==delay3)) begin
a_reg <= (a_reg>>1);
end
else begin
if((state==delay2)) begin
a_reg <= (a_reg<<1);
end
else begin
if((state==delay1)) begin
if(en_scramb) begin
a_reg <= a_scramb;
end
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
if(en_scramb) begin
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

endmodule
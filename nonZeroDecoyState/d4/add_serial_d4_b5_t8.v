module add_serial(b,out,en,a,rst,clk);
parameter [31:0] delay0 = 'd3;
wire [7:0] a_scramb;
input wire [7:0] b;
reg [0:0] carry;
wire [7:0] b_scramb;
output reg [7:0] out;
reg [7:0] b_reg;
reg [7:0] a_reg;
reg [2:0] state;
parameter [1:0] ADD = 'd1;
parameter [31:0] delay3 = 'd6;
reg [2:0] count;
input wire [7:0] a;
wire [0:0] sum;
parameter [1:0] IDLE = 'd0;
parameter [31:0] delay1 = 'd4;
input wire [0:0] en;
input wire [0:0] rst;
parameter [31:0] delay2 = 'd5;
input wire [0:0] clk;
parameter [1:0] DONE = 'd2;
assign a_scramb = {a[7],a[6],a[5],a[4],(~a[3]),a[2],(~a[1]),a[0]};
assign b_scramb = {(~b[7]),(~b[6]),(~b[5]),(~b[4]),(~b[3]),(~b[2]),b[1],b[0]};
assign sum = ((a_reg[0]^b_reg[0])^carry);
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
end
else begin
if((state==delay1)) begin
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
end
end
end

always @(posedge clk or posedge rst) begin
if(rst) begin
b_reg <= 0;
end
else begin
if((state==delay3)) begin
b_reg <= (b_reg<<1);
end
else begin
if((state==delay2)) begin
end
else begin
if((state==delay1)) begin
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
end
end
end

always @(posedge clk or posedge rst) begin
if(rst) begin
state <= IDLE;
end
else begin
if((state==delay3)) begin
if((((~b[7])&&(~a[5]))&&b[5])) begin
state <= ADD;
end
else begin
if((((~b[7])&&a[5])&&b[6])) begin
state <= delay0;
end
else begin
if((((~b[7])&&a[5])&&(~b[6]))) begin
state <= IDLE;
end
else begin
if((((~b[7])&&(~a[5]))&&(~b[5]))) begin
state <= delay2;
end
else begin
if((b[7]&&(~b[6]))) begin
state <= delay1;
end
else begin
if(((b[7]&&b[6])&&a[6])) begin
state <= DONE;
end
else begin
if(((b[7]&&b[6])&&(~a[6]))) begin
state <= delay3;
end
end
end
end
end
end
end
end
else begin
if((state==delay2)) begin
if((((~a[5])&&b[4])&&a[2])) begin
state <= delay2;
end
else begin
if((((~a[5])&&(~b[4]))&&(~a[2]))) begin
state <= delay1;
end
else begin
if((((~a[5])&&(~b[4]))&&a[2])) begin
state <= IDLE;
end
else begin
if(((a[5]&&(~en[0]))&&b[7])) begin
state <= delay3;
end
else begin
if(((a[5]&&(~en[0]))&&(~b[7]))) begin
state <= DONE;
end
else begin
if((a[5]&&en[0])) begin
state <= delay0;
end
else begin
if((((~a[5])&&b[4])&&(~a[2]))) begin
state <= ADD;
end
end
end
end
end
end
end
end
else begin
if((state==delay1)) begin
if(((b[1]&&(~b[4]))&&(~en[0]))) begin
state <= DONE;
end
else begin
if((((~b[1])&&(~b[5]))&&a[6])) begin
state <= ADD;
end
else begin
if((((~b[1])&&(~b[5]))&&(~a[6]))) begin
state <= delay2;
end
else begin
if((((~b[1])&&b[5])&&(~a[7]))) begin
state <= delay1;
end
else begin
if(((b[1]&&(~b[4]))&&en[0])) begin
state <= delay3;
end
else begin
if((((~b[1])&&b[5])&&a[7])) begin
state <= IDLE;
end
else begin
if((b[1]&&b[4])) begin
state <= delay0;
end
end
end
end
end
end
end
end
else begin
if((state==delay0)) begin
if((((~b[6])&&(~b[1]))&&a[2])) begin
state <= DONE;
end
else begin
if(((b[6]&&(~b[7]))&&b[1])) begin
state <= delay2;
end
else begin
if((((~b[6])&&(~b[1]))&&(~a[2]))) begin
state <= delay3;
end
else begin
if((b[6]&&b[7])) begin
state <= delay0;
end
else begin
if((((~b[6])&&b[1])&&(~b[3]))) begin
state <= IDLE;
end
else begin
if((((~b[6])&&b[1])&&b[3])) begin
state <= delay1;
end
else begin
if(((b[6]&&(~b[7]))&&(~b[1]))) begin
state <= ADD;
end
end
end
end
end
end
end
end
else begin
if((state==DONE)) begin
if((((en>'d0)&&(~b[7]))&&(~a[7]))) begin
state <= IDLE;
end
else begin
if((((!(en>'d0))&&a[2])&&a[3])) begin
state <= delay3;
end
else begin
if(((!(en>'d0))&&(~a[2]))) begin
state <= delay0;
end
else begin
if((((en>'d0)&&b[7])&&(~b[0]))) begin
state <= ADD;
end
else begin
if((((!(en>'d0))&&a[2])&&(~a[3]))) begin
state <= DONE;
end
else begin
if((((en>'d0)&&(~b[7]))&&a[7])) begin
state <= delay1;
end
else begin
if((((en>'d0)&&b[7])&&b[0])) begin
state <= delay2;
end
end
end
end
end
end
end
end
else begin
if((state==ADD)) begin
if(((((!(count=='d7))&&b[2])&&a[5])&&(~b[5]))) begin
state <= delay1;
end
else begin
if((count=='d7)) begin
state <= delay1;
end
else begin
if(((((!(count=='d7))&&b[2])&&(~a[5]))&&b[4])) begin
state <= DONE;
end
else begin
if(((((!(count=='d7))&&b[2])&&a[5])&&b[5])) begin
state <= IDLE;
end
else begin
if(((((!(count=='d7))&&b[2])&&(~a[5]))&&(~b[4]))) begin
state <= delay3;
end
else begin
if(((((!(count=='d7))&&(~b[2]))&&(~b[5]))&&b[7])) begin
state <= ADD;
end
else begin
if(((((!(count=='d7))&&(~b[2]))&&(~b[5]))&&(~b[7]))) begin
state <= delay2;
end
else begin
if((((!(count=='d7))&&(~b[2]))&&b[5])) begin
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
else begin
if((state==IDLE)) begin
if((((en>'d0)&&(~b[2]))&&(~a[0]))) begin
state <= DONE;
end
else begin
if((((!(en>'d0))&&b[0])&&(~b[6]))) begin
state <= IDLE;
end
else begin
if((((!(en>'d0))&&(~b[0]))&&b[1])) begin
state <= delay2;
end
else begin
if(((en>'d0)&&b[2])) begin
state <= delay0;
end
else begin
if((((!(en>'d0))&&b[0])&&b[6])) begin
state <= delay1;
end
else begin
if((((!(en>'d0))&&(~b[0]))&&(~b[1]))) begin
state <= ADD;
end
else begin
if((((en>'d0)&&(~b[2]))&&a[0])) begin
state <= delay3;
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
count <= (count+{a[1],a[7],a[4]});
end
else begin
if((state==delay2)) begin
end
else begin
if((state==delay1)) begin
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
end
end
end

always @(posedge clk or posedge rst) begin
if(rst) begin
carry <= 0;
end
else begin
if((state==delay3)) begin
carry <= (((a_reg[0]&b_reg[0])&(a_reg[0]&carry))&(b_reg[0]&carry));
end
else begin
if((state==delay2)) begin
end
else begin
if((state==delay1)) begin
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
end
else begin
if((state==delay1)) begin
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
end
end
end

endmodule
// module add(a, b, out);
  // input   [7:0] a;
  // input   [7:0] b;
  // output  [7:0] out;

  // wire  [7:0] a;
  // wire  [7:0] b;
  // wire  [7:0] out;

  // assign out = a + b;

// endmodule

module add_serial(a, b, clk, rst, en, out);
  input   [7:0] a, b;
  input   clk, rst, en;
  output  [7:0] out;

  wire  [7:0] a, b;
  wire  clk, rst, en;
  reg   [7:0] out;

  // internals
  reg   [7:0] a_reg, b_reg;
  reg   carry;
  wire  sum;
  reg   [2:0] count;

  // states
  parameter [1:0] IDLE  = 2'd0;
  parameter [1:0] ADD   = 2'd1;
  parameter [1:0] DONE  = 2'd2;
  reg [1:0] state;
  
  always @(posedge clk or posedge rst) begin
    if (rst) state <= IDLE;
    else
      case (state)
        IDLE: state <= (en) ? ADD : IDLE;
        ADD:  state <= (count == 7) ? DONE : ADD;
        DONE: state <= (en) ? IDLE : DONE;
      endcase
  end
  
  always @(posedge clk or posedge rst) begin
    if (rst) begin
      out <= 0;
      a_reg <= 0;
      b_reg <= 0;
      carry <= 0;
      count <= 0;
      // state <= IDLE;
      // s1 <= 0;
      // s0 <= 0;
    end else begin
      case(state)
      // case ({s1,s0})
        IDLE: begin
        // 2'b00: begin
          if (en) begin
            out <= 0;
            a_reg <= a;
            b_reg <= b;
            carry <= 0;
            count <= 0;
            // state <= ADD;
            // s1 <= 0;
            // s0 <= 1;
          end
        end
        ADD: begin
        // 2'b01: begin
          a_reg <= a_reg >> 1;
          b_reg <= b_reg >> 1;
          carry <= (a_reg[0]&b_reg[0]) | (a_reg[0]&carry) | (b_reg[0]&carry);
          out <= {sum, out[7:1]};
          count <= count + 1;
          // state <= (count == 7) ? DONE : ADD;
          // s1 <= (count == 7) ? 1 : 0;
          // s0 <= (count == 7) ? 0 : 1;
        end
        // DONE: begin
        // 2'b10: begin
          // casex ({a[0],b[0]})
            // 2'b?1: state <= IDLE;
            // 2'b00: state <= DONE;
            // 2'b10: state <= ADD;
          // endcase
          // state <= (en) ? IDLE : DONE;
          // s1 <= (en) ? 0 : 1;
          // s0 <= 0;
        // end
        // default: begin
          // out <= 0;
          // a_reg <= 0;
          // b_reg <= 0;
          // carry <= 0;
          // count <= 0;
          // state <= IDLE;
        // end
      endcase
    end
  end

  assign sum = a_reg[0] ^ b_reg[0] ^ carry;

endmodule

/*
module tb_add_serial;
  reg   [7:0] a, b;
  wire  [7:0] out;
  reg   clk, rst, en;

  add_serial dut(.a(a), .b(b), .clk(clk), .rst(rst), .en(en), .out(out));

  initial begin
    clk = 1;
    forever #5 clk = ~clk;
  end

  initial begin
    $monitor($time,, "a=%b, b=%b, out=%b", a, b, out);
    rst = 1; rst <= 0;
    a = 5; b = 3; en = 1;
    @(posedge clk);
    en <= 0;
    repeat (20) @(posedge clk);
    $finish;
  end

endmodule
*/

// module tb_add;
  // [7:0] a, b, out;

  // add dut(.*);

  // initial begin
    // a = 50; b = 23;
    // #100;
    // $display("out = %d", out);
    // $finish;
  // end

// endmodule

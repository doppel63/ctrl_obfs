from __future__ import absolute_import
from __future__ import print_function
import sys
import os
##from optparse import OptionParser

# the next line can be removed after installation
##sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyverilog.utils.version
from pyverilog.dataflow.dataflow_analyzer import VerilogDataflowAnalyzer
from pyverilog.dataflow.optimizer import VerilogDataflowOptimizer
##from pyverilog.dataflow.graphgen import VerilogGraphGenerator
from pyverilog.controlflow.controlflow_analyzer import VerilogControlflowAnalyzer

import pyverilog.dataflow.dataflow as DF
import prune
import ControlDataFlowGraph as CDFG

import random
import copy
import os
import shutil
import errno

random.seed('ACTL')

def main():
##    CIRCUIT = "dma_rrarb"
    CIRCUIT = "add_serial"

    if CIRCUIT == "dma_rrarb":
        src = "dma_rrarb/"
        filelist = ["dma_rrarb_mod.v"]
        topmodule = "dma_rrarb"
    elif CIRCUIT == "add_serial":
        src = "add_serial/"        
        filelist = ["add_serial_mod.v"]
        topmodule = "add_serial"
    dst = "./"
    new_files = []
    for file_name in os.listdir(src):
        full_file_name = os.path.join(src, file_name)
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, dst)
            new_files.append(file_name)
    
    noreorder = False
    nobind = False
    include = []
    define = []

    analyzer = VerilogDataflowAnalyzer(filelist, topmodule, noreorder, nobind,
                                       include, define)
    analyzer.generate()

##    directives = analyzer.get_directives()
    terms = analyzer.getTerms()
    binddict = analyzer.getBinddict()

    optimizer = VerilogDataflowOptimizer(terms, binddict)
    optimizer.resolveConstant()
    resolved_terms = optimizer.getResolvedTerms()
    resolved_binddict = optimizer.getResolvedBinddict()
    constlist = optimizer.getConstlist()

    fsm_vars = tuple(['state'])
    canalyzer = VerilogControlflowAnalyzer(topmodule, terms, binddict,
                                           resolved_terms, resolved_binddict,
                                           constlist, fsm_vars)
    fsms = canalyzer.getFiniteStateMachines()
    
    name = topmodule
    if CIRCUIT == "dma_rrarb":
        state_var = CDFG.newScope('dma_rrarb', 'state')
        clk = CDFG.newScope('dma_rrarb', 'HCLK')
        rst = CDFG.newScope('dma_rrarb', 'HRSTn')
        state_list = [
            CDFG.newScope('dma_rrarb', 'grant0'),
            CDFG.newScope('dma_rrarb', 'grant1'),
            CDFG.newScope('dma_rrarb', 'grant2'),
            CDFG.newScope('dma_rrarb', 'grant3'),
            CDFG.newScope('dma_rrarb', 'grant4'),
            CDFG.newScope('dma_rrarb', 'grant5'),
            CDFG.newScope('dma_rrarb', 'grant6'),
            CDFG.newScope('dma_rrarb', 'grant7'),
        ]
    elif CIRCUIT == "add_serial":
        state_var = CDFG.newScope('add_serial', 'state')
        clk = CDFG.newScope('add_serial', 'clk')
        rst = CDFG.newScope('add_serial', 'rst')
        state_list = [
            CDFG.newScope('add_serial', 'IDLE'),
            CDFG.newScope('add_serial', 'ADD'),
            CDFG.newScope('add_serial', 'DONE')
        ]

    max_trials = 20
    max_bits = 6
    max_num_ex_states = 8

    for num_ex_states in range(max_num_ex_states + 1):
##    for num_ex_states in [3,4,5]:
        print("num_ex_states = " + str(num_ex_states))
        codegen_dir = "{}/codegen/nonZeroCopyState/d{}/".format(topmodule, num_ex_states)
        try:
            os.makedirs(codegen_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        f = open(codegen_dir + "edge_count_d{}.csv".format(num_ex_states),"w")
        for i in range(max_bits):
            num_bits = i + 1
            for trial in range(max_trials):
                print("generating code for num_bits = {}, trial = {}".format(
                    num_bits, trial+1))
                fsm_obj = copy.deepcopy(fsms[state_var])
                cur_state_list = copy.deepcopy(state_list)
                cur_constlist = copy.deepcopy(constlist)
                cur_terms = copy.deepcopy(resolved_terms)
                cur_binddict = copy.deepcopy(resolved_binddict)

                cdfg =\
                     CDFG.ControlDataFlowGraph(name, fsm_obj, state_var, clk, rst,
                                               cur_state_list, cur_constlist,
                                               cur_terms, cur_binddict)
                cdfg.generate()            
                PIs = cdfg.getPIs()
                # exempt clk
                PIs.remove(cdfg.clk)
                # and reset from scrambling
                if cdfg.rst:
                    PIs.remove(cdfg.rst)
                total_bits = 0
                for PI in PIs:
                    total_bits += cdfg.getNumBitsOfVar(PI)                
                cdfg.scramblePIBits(total_bits/2)
                for ex_state_i in range(num_ex_states):
                    src = cdfg.state_list[ex_state_i]
                    dst = cdfg.state_list[ex_state_i+1]
                    delay = CDFG.newScope(topmodule, 'delay'+str(ex_state_i))
##                    cdfg.insDelayState(src, dst, delay)
                    cdfg.insCopyState(src, dst, delay)
                (all_trans_freqs, num_PIs) = cdfg.getTransFreqs()
                for state in cur_state_list:
                    src_i = cdfg.state_list.index(state)
                    trans_freqs = all_trans_freqs[src_i]
                    trans_freqs = cdfg.nonZeroStates(trans_freqs, state, num_bits)
                    all_trans_freqs[src_i] = trans_freqs
                cdfg.toCode(topmodule,
                            codegen_dir + "{}_d{}_b{}_t{}.v"
                            .format(topmodule, num_ex_states, num_bits, trial+1))
                metric_val = cdfg.countConnects(all_trans_freqs)
                f.write(str(metric_val)+",")
            f.write("\n")
        f.close()

    print("\n")
    print("done")

    for file_name in new_files:
        os.remove(file_name)

if __name__ == '__main__':
    main()

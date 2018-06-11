from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from optparse import OptionParser

# the next line can be removed after installation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyverilog.utils.version
from pyverilog.dataflow.dataflow_analyzer import VerilogDataflowAnalyzer
from pyverilog.dataflow.optimizer import VerilogDataflowOptimizer
from pyverilog.dataflow.graphgen import VerilogGraphGenerator
from pyverilog.controlflow.controlflow_analyzer import VerilogControlflowAnalyzer

from pyverilog.controlflow.controlflow_analyzer import FiniteStateMachine
import pyverilog.utils.util as util
import pyverilog.controlflow.transition as transition

import pyverilog.dataflow.dataflow as DF
import prune
import ControlDataFlowGraph as CDFG

import random

random.seed('ACTL')

##CIRCUIT = "add_serial"
##CIRCUIT = "bbara"
##CIRCUIT = "dma_rrarb"
##CIRCUIT = "mc_timing"
##CIRCUIT = "correlator"

def main():
    INFO = "Verilog module signal/module dataflow analyzer"
    VERSION = pyverilog.utils.version.VERSION
    USAGE = "Usage: python example_dataflow_analyzer.py -t TOPMODULE file ..."

    def showVersion():
        print(INFO)
        print(VERSION)
        print(USAGE)
        sys.exit()
    
    optparser = OptionParser()
    optparser.add_option("-v","--version",action="store_true",dest="showversion",
                         default=False,help="Show the version")
    optparser.add_option("-I","--include",dest="include",action="append",
                         default=[],help="Include path")
    optparser.add_option("-D",dest="define",action="append",
                         default=[],help="Macro Definition")
    optparser.add_option("-t","--top",dest="topmodule",
                         default="TOP",help="Top module, Default=TOP")
    optparser.add_option("--nobind",action="store_true",dest="nobind",
                         default=False,help="No binding traversal, Default=False")
    optparser.add_option("--noreorder",action="store_true",dest="noreorder",
                         default=False,help="No reordering of binding dataflow, Default=False")
    (options, args) = optparser.parse_args()

    filelist = args
    if options.showversion:
        showVersion()

    for f in filelist:
        if not os.path.exists(f): raise IOError("file not found: " + f)

    if len(filelist) == 0:
        showVersion()

    analyzer = VerilogDataflowAnalyzer(filelist, options.topmodule,
                                       noreorder=options.noreorder,
                                       nobind=options.nobind,
                                       preprocess_include=options.include,
                                       preprocess_define=options.define)
    analyzer.generate()

    CIRCUIT = options.topmodule

    directives = analyzer.get_directives()
    terms = analyzer.getTerms()
    binddict = analyzer.getBinddict()

    optimizer = VerilogDataflowOptimizer(terms, binddict)

    optimizer.resolveConstant()
    resolved_terms = optimizer.getResolvedTerms()
    resolved_binddict = optimizer.getResolvedBinddict()
    constlist = optimizer.getConstlist()

    top = options.topmodule
    fsm_vars = tuple(['state'])
##    fsm_vars = tuple(['dpll_state'])
##    fsm_vars = tuple(['s1','s0'])
    canalyzer = VerilogControlflowAnalyzer(options.topmodule, terms, binddict,
                                           resolved_terms, resolved_binddict,
                                           constlist, fsm_vars)
    fsms = canalyzer.getFiniteStateMachines()
    print("")
    
    name = 'test'

    if CIRCUIT == "add_serial":
        state_var = CDFG.newScope('add_serial', 'state')
        clk = CDFG.newScope('add_serial', 'clk')
        rst = CDFG.newScope('add_serial', 'rst')
    elif CIRCUIT == "bbara":
        state_var = CDFG.newScope('top', 'state')
        clk = CDFG.newScope('top', 'clk')
        rst = None
    elif CIRCUIT == "dma_rrarb":
        state_var = CDFG.newScope('dma_rrarb', 'state')
        clk = CDFG.newScope('dma_rrarb', 'HCLK')
        rst = CDFG.newScope('dma_rrarbrb', 'HRSTn')
    elif CIRCUIT == "mc_timing":
        state_var = CDFG.newScope('mc_timing', 'state')
        clk = CDFG.newScope('mc_timing', 'clk')
        rst = CDFG.newScope('mc_timing', 'rst')
    elif CIRCUIT == "correlator":
        state_var = CDFG.newScope('correlator', 'state')
        clk = CDFG.newScope('correlator', 'clk')
        rst = CDFG.newScope('correlator', 'rst_n')

    fsm_obj = fsms[state_var]

    if CIRCUIT == "add_serial":
        state_list = [
            CDFG.newScope('add_serial', 'IDLE'),
            CDFG.newScope('add_serial', 'ADD'),
            CDFG.newScope('add_serial', 'DONE')
        ]
    elif CIRCUIT == "bbara":
        state_list = [
            CDFG.newScope('top', 'st0'),
            CDFG.newScope('top', 'st1'),
            CDFG.newScope('top', 'st2'),
            CDFG.newScope('top', 'st3'),
            CDFG.newScope('top', 'st4'),
            CDFG.newScope('top', 'st5'),
            CDFG.newScope('top', 'st6'),
            CDFG.newScope('top', 'st7'),
            CDFG.newScope('top', 'st8'),
            CDFG.newScope('top', 'st9')
        ]
    elif CIRCUIT == "dma_rrarb":
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
    elif CIRCUIT == "mc_timing":
        state_list = [
            CDFG.newScope('mc_timing', 'POR'),
            CDFG.newScope('mc_timing', 'IDLE'),		
            CDFG.newScope('mc_timing', 'IDLE_T'),
            CDFG.newScope('mc_timing', 'IDLE_T2'),
            CDFG.newScope('mc_timing', 'PRECHARGE'),
            CDFG.newScope('mc_timing', 'PRECHARGE_W'),
            CDFG.newScope('mc_timing', 'ACTIVATE'),
            CDFG.newScope('mc_timing', 'ACTIVATE_W'),
            CDFG.newScope('mc_timing', 'SD_RD_WR'),
            CDFG.newScope('mc_timing', 'SD_RD'),
            CDFG.newScope('mc_timing', 'SD_RD_W'),
            CDFG.newScope('mc_timing', 'SD_RD_LOOP'),
            CDFG.newScope('mc_timing', 'SD_RD_W2'),
            CDFG.newScope('mc_timing', 'SD_WR'),
            CDFG.newScope('mc_timing', 'SD_WR_W'),
            CDFG.newScope('mc_timing', 'BT'),
            CDFG.newScope('mc_timing', 'BT_W'),
            CDFG.newScope('mc_timing', 'REFR'),
            CDFG.newScope('mc_timing', 'LMR0'),
            CDFG.newScope('mc_timing', 'LMR1'),
            CDFG.newScope('mc_timing', 'LMR2'),
            CDFG.newScope('mc_timing', 'INIT0'),
            CDFG.newScope('mc_timing', 'INIT'),
            CDFG.newScope('mc_timing', 'INIT_W'),
            CDFG.newScope('mc_timing', 'INIT_REFR1'),
            CDFG.newScope('mc_timing', 'INIT_REFR1_W'),
            CDFG.newScope('mc_timing', 'INIT_LMR'),
            CDFG.newScope('mc_timing', 'SUSP1'),
            CDFG.newScope('mc_timing', 'SUSP2'),
            CDFG.newScope('mc_timing', 'SUSP3'),
            CDFG.newScope('mc_timing', 'SUSP4'),
            CDFG.newScope('mc_timing', 'RESUME1'),
            CDFG.newScope('mc_timing', 'RESUME2'),
            CDFG.newScope('mc_timing', 'BG0'),
            CDFG.newScope('mc_timing', 'BG1'),
            CDFG.newScope('mc_timing', 'BG2'),
            CDFG.newScope('mc_timing', 'ACS_RD'),
            CDFG.newScope('mc_timing', 'ACS_RD1'),
            CDFG.newScope('mc_timing', 'ACS_RD2A'),
            CDFG.newScope('mc_timing', 'ACS_RD2'),
            CDFG.newScope('mc_timing', 'ACS_RD3'),
            CDFG.newScope('mc_timing', 'ACS_RD_8_1'),
            CDFG.newScope('mc_timing', 'ACS_RD_8_2'),
            CDFG.newScope('mc_timing', 'ACS_RD_8_3'),
            CDFG.newScope('mc_timing', 'ACS_RD_8_4'),
            CDFG.newScope('mc_timing', 'ACS_RD_8_5'),
            CDFG.newScope('mc_timing', 'ACS_RD_8_6'),
            CDFG.newScope('mc_timing', 'ACS_WR'),
            CDFG.newScope('mc_timing', 'ACS_WR1'),
            CDFG.newScope('mc_timing', 'ACS_WR2'),
            CDFG.newScope('mc_timing', 'ACS_WR3'),
            CDFG.newScope('mc_timing', 'ACS_WR4'),
            CDFG.newScope('mc_timing', 'SRAM_RD'),
            CDFG.newScope('mc_timing', 'SRAM_RD0'),
            CDFG.newScope('mc_timing', 'SRAM_RD1'),
            CDFG.newScope('mc_timing', 'SRAM_RD2'),
            CDFG.newScope('mc_timing', 'SRAM_RD3'),
            CDFG.newScope('mc_timing', 'SRAM_RD4'),
            CDFG.newScope('mc_timing', 'SRAM_WR'),
            CDFG.newScope('mc_timing', 'SRAM_WR0'),
            CDFG.newScope('mc_timing', 'SCS_RD'),
            CDFG.newScope('mc_timing', 'SCS_RD1'),
            CDFG.newScope('mc_timing', 'SCS_RD2'),
            CDFG.newScope('mc_timing', 'SCS_WR'),
            CDFG.newScope('mc_timing', 'SCS_WR1'),
            CDFG.newScope('mc_timing', 'SCS_ERR')
        ]
    elif CIRCUIT == "correlator":
        state_list = [
            CDFG.newScope('correlator', 'WAITING'),
            CDFG.newScope('correlator', 'DECIDING'),
            CDFG.newScope('correlator', 'OFFSETTING'),
            CDFG.newScope('correlator', 'RUNNING'),
            CDFG.newScope('correlator', 'IDLE'),
            CDFG.newScope('correlator', 'LOCKED'),
            CDFG.newScope('correlator', 'READ_RANK'),
            CDFG.newScope('correlator', 'default')
        ]

    cdfg =\
         CDFG.ControlDataFlowGraph(name, fsm_obj, state_var, clk, rst,
                                   state_list, constlist,
                                   resolved_terms, resolved_binddict)
    cdfg.generate()

    # fsm
    cdfg.fsm_obj.view()
    print("")

    PIs = cdfg.getPIs()
    # exempt clk
    PIs.remove(cdfg.clk)
    # and reset from scrambling
    if cdfg.rst:
        PIs.remove(cdfg.rst)
    total_bits = 0
    for PI in PIs:
        total_bits += cdfg.getNumBitsOfVar(PI)
    print("number of scrambled bits: " + str(total_bits/2))
    cdfg.scramblePIBits(total_bits/2)

    num_ex_states = 1
    for ex_state_i in range(num_ex_states):
        src = cdfg.state_list[ex_state_i]
        dst = cdfg.state_list[ex_state_i+1]
        delay = CDFG.newScope(top, 'delay'+str(ex_state_i))
##        delay = CDFG.newScope('add_serial', 'delay'+str(ex_state_i))
        cdfg.insCopyState(src, dst, delay)
##        cdfg.insDelayState(src, dst, delay)

    num_bits = 6
    # nonZeroStates test
    (all_trans_freqs, num_PIs) = cdfg.getTransFreqs()
    for row in all_trans_freqs:
        print(row)
    print("")
    for i in range(len(cdfg.state_list)):
        trans_freqs = cdfg.nonZeroStates(all_trans_freqs[i],\
                                         cdfg.state_list[i], num_bits)
        all_trans_freqs[i] = trans_freqs
##    (all_trans_freqs, num_PIs) = cdfg.getTransFreqs()
    for row in all_trans_freqs:
        print(row)
    print("")

##    cdfg.toCode(options.topmodule, options.topmodule + '_codegen.v')

##    cdfg.toCode('add_serial', 'add_serial_uniform.v')

##    cdfg.toCode('add_serial', 'add_serial_scramb.v')

##    cdfg.updateBinddict()
##    cdfg.toCode('dma_rrarb', 'dma_rrarb_uniform_s0.v')
    
##    cdfg.updateBinddict()
##    cdfg.toCode('dma_rrarb', 'dma_rrarb_scramb_s0_b{}.v'
##                .format(num_bits))
##    cdfg.toCode('dma_rrarb', 'dma_rrarb_scramb_delay_b{}.v'.format(num_bits))

    print("\n")
##    print("num_edits = {}".format(num_edits))

##    # original binds
##    for var, bind in cdfg.binddict.items():
##        print(var)
##        print(bind[0].tostr())
####        print(bind[0].isCombination())
####        print(bind[0].alwaysinfo)
####        print(bind[0].parameterinfo)
##    print("")
##
    # binds by state
    for state, binddict in cdfg.state_binddict.items():
        print(state)
        for var, binds in binddict.items():
            print(var)
            for bind in binds:
                print(bind.tostr())
##                print(bind.dest)
##                print(type(bind.dest))
##                print(bind.msb)
##                print(type(bind.msb))
##                print(bind.lsb)
##                print(type(bind.lsb))
##                print(bind.ptr)
##                print(type(bind.ptr))
##                print(bind.alwaysinfo)
##                print(type(bind.alwaysinfo))
##                print(bind.parameterinfo)
##                print(type(bind.parameterinfo))
##                print("")
        print("")
    print("")
        
##    # terms
##    for k, v in cdfg.terms.items():
##        print(k)
####        print(k.scopechain[-1].scopename)
####        print(k.scopechain[-1].scopetype)
####        print(k.scopechain[-1].scopeloop)
##        print(v.name)
##        print(type(v.name))
##        print(v.termtype)
##        for item in v.termtype:
##            print(type(item))
##        print(v.msb)
##        print(type(v.msb))
##        print(v.lsb)
##        print(type(v.lsb))
##        print(v.lenmsb)
##        print(v.lenlsb)
##        print(v.tocode())
##        print("")

##    # fsm
##    cdfg.fsm_obj.view()
##    print("")

    # fsm trans
##    for src, transdict in cdfg.fsm_obj.fsm.items():
##        print(src)
##        for cond, dst in transdict.items():
##            print(cond.tostr())
####            trans = repr(src) + "--" + repr(cond)
####            if cond:
####                trans += ":" + repr(cond.nextnodes)
######                for node in cond.nextnodes:
######                    if isinstance(node, DF.DFEvalValue):
######                        print("eval")
######                        print(node.value)
######                        print(type(node.value))
####            trans += "-->" + repr(dst)
####            print(trans)
##        print("")
##    print("")

##    # fsm original
##    cdfg.fsm_ori.view()
##    print("")
##    for src, transdict in cdfg.fsm_ori.fsm.items():
##        print(src)
##        for cond, dst in transdict.items():
##            trans = repr(src) + "--" + repr(cond)
##            if cond:
##                trans += ":" + repr(cond.nextnodes)
##            trans += "-->" + repr(dst)
##            print(trans)
##        print("")
##    print("")

##    # conditions
##    for (src_i,dst_i), var_dict in cdfg.conditions.items():
##        print("{}->{}:".format(src_i,dst_i))
##        for var,constrs in var_dict.items():
##            print("\t{}:".format(var))
##            for constr in constrs:
##                print("\t\t[{}] = {}".format(constr[0], constr[1]))

##    # input mapping test
##    a = CDFG.newScope('add_serial','a')
##    b = CDFG.newScope('add_serial','b')
##    en = CDFG.newScope('add_serial','en')
##    inputs = [ ({en: '1', a:'00000101', b:'00000011'},(0,1)),
##               ({en: '0', a:'00000101', b:'00000011'},(1,1)),
##               ({en: '0', a:'00000101', b:'00000011'},(1,1)),
##               ({en: '0', a:'00000101', b:'00000011'},(1,1)),
##               ({en: '0', a:'00000101', b:'00000011'},(1,1)),
##               ({en: '0', a:'00000101', b:'00000011'},(1,1)),
##               ({en: '0', a:'00000101', b:'00000011'},(1,1)),
##               ({en: '0', a:'00000101', b:'00000011'},(1,1)),
##               ({en: '0', a:'00000101', b:'00000011'},(1,2)),
##               ({en: '0', a:'00000222', b:'00000222'},(2,2)),
##               ({en: '1', a:'00000222', b:'00000222'},(2,0))
##                ]
##    new_inputs = cdfg.mapInputs(inputs)
##    for (pattern, (src_i,dst_i)) in new_inputs:
##        print("{}, ({},{})".format(pattern, src_i, dst_i))
##    # input mapping test
##    next_ch = CDFG.newScope('dma_rrarb','next_ch')
##    i0 = CDFG.newScope('dma_rrarb','vld_req0')
##    i1 = CDFG.newScope('dma_rrarb','vld_req1')
##    i2 = CDFG.newScope('dma_rrarb','vld_req2')
##    i3 = CDFG.newScope('dma_rrarb','vld_req3')
##    i4 = CDFG.newScope('dma_rrarb','vld_req4')
##    i5 = CDFG.newScope('dma_rrarb','vld_req5')
##    i6 = CDFG.newScope('dma_rrarb','vld_req6')
##    i7 = CDFG.newScope('dma_rrarb','vld_req7')
##    inputs = [({next_ch: '0',
##                i0:'1', i1:'0', i2:'1', i3:'1',
##                i4:'1', i5:'1', i6:'0', i7:'1'},(0,0))
##              # output should be: 1_1111_1010 when next_ch, 1, 5, 6, 7 flipped
##                ]
##    new_inputs = cdfg.mapInputs(inputs)
##    for (pattern, (src_i,dst_i)) in new_inputs:
##        print("{}, ({},{})".format(pattern, src_i, dst_i))

##    for cond, dst in cdfg.fsm_obj.fsm[0].items():
##        print(cond.tostr())
##        print(dst)
##    test_cond = cdfg.fsm_obj.fsm[0].items()[0][0]
##    print(test_cond.tostr())
##    print(cdfg.evalCond(test_cond, inputs[0][0]))

    # edge count test
##    total_edges = cdfg.countEdges(cdfg.fsm_obj.fsm)
##    print(total_edges)
##    total_sub_FSMs = cdfg.countSubFSMs(cdfg.fsm_obj.fsm)
##    print(total_sub_FSMs)

##    # frequency table test
##    for src_list in init_freqs:
##        print(src_list)
##    print("")
##    init_freqs = cdfg.normalizeTransFreqs(init_freqs, num_PIs)
##    (freqs, num_PIs) = cdfg.getTransFreqs()
##    for src_list in init_freqs:
##        print(src_list)
##    print("")
##    for src_list in freqs:
##        print(src_list)
##    print("")
##    freqs = cdfg.normalizeTransFreqs(freqs, num_PIs)
##    for src_list in freqs:
##        print(src_list)
##    print("")
##    
##    for state_freqs in freqs:
##        print(cdfg.scoreClosestNSF(init_freqs[0], state_freqs))
##
##    print("")
##    print(cdfg.scoreAllNSF(init_freqs, freqs))
##
##    print("")
##    print(cdfg.getEarthMoversDistance([1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],
##                                      [0.0,0.0,0.0,0.0,0.0,0.0,0.0,1.0]))

##    # classifier test
##    cdfg.trainClassifiers("dma_rrarb/data")
##    scores = cdfg.evalCurrentFSM()
##    print(scores)

##    # constlist
##    for k, v in cdfg.constlist.items():
##        print(k)
##        print(type(k))
##        for label in k.scopechain:
##            print(label.scopetype)
##        print(v)
##        print(type(v))
##        print("")

##    # state_dict
##    for k, v in cdfg.state_dict.items():
##        print(k)
##        print(v)
##        print(type(v))
##        print("")

##    # state_list
##    for i in range(len(cdfg.state_list)):
##        print(i)
##        print(cdfg.state_list[i])

##    # generate training data for per-state classifiers
##    cdfg.generateStateData("dma_rrarb/data")

##    options.searchtarget = ['add_serial.state']
##    options.outputfile = 'add_serial_state_updated_binddict.png'
##    options.searchtarget = ['dma_rrarb.next_state']
##    options.outputfile = 'dma_rrarb_next_state.png'
##    options.walk = False
##    options.identical = False
##    options.step = 1
##    options.reorder = False
##    options.delay = False
##        
##    graphgen = VerilogGraphGenerator(options.topmodule, terms, binddict, 
##                                     resolved_terms, resolved_binddict,
##                                     constlist, options.outputfile)
##    for target in options.searchtarget:
##        graphgen.generate(target, walk=options.walk,
##                          identical=options.identical, step=options.step,
##                          reorder=options.reorder, delay=options.delay)
##
##    graphgen.draw()

if __name__ == '__main__':
    main()

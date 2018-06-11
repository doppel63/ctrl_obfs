import copy
import math
import random
import Queue
import itertools
import csv
import numpy as np

from sklearn.ensemble import RandomForestClassifier

import pyverilog
import pyverilog.dataflow.dataflow as DF
import prune

class ControlDataFlowGraph(object):
    def __init__(self, name, fsm_obj, state_var, clk, rst, state_list,
                 constlist, terms, binddict):
        self.name = name
        self.fsm_obj = fsm_obj          # FiniteStateMachine instance
        self.state_var = state_var      # ScopeChain of state variable
        self.clk = clk                  # ScopeChain of state variable
        self.rst = rst                  # ScopeChain of state variable
        self.state_list = state_list    # list of ScopeChains. for translating
                                        # from int to scopechains for states
        self.constlist = constlist      # constlist from pyverilog
        self.terms = terms
        self.binddict = binddict
        self.state_binddict = {}        # dict[state in int] = binddict by state
        self.conditions = {}            # dict[(src_i,dst_i)][var in scopechain]
                                        # = [(bit_pos, constrained_val)]
        self.trans_freqs = []
        self.classifiers = []

    def generate(self):
        state_i_list = self.fsm_obj.fsm.keys()
        # create copies of each dataflow (binds) for each state
        for state_i in state_i_list:
            cur_binddict = copy.deepcopy(self.binddict)
            state_val = self.state_list[state_i]
            for bindname, bindlist in cur_binddict.items():
                for bind in bindlist:
                    prune.pruneBind(bind, repr(self.state_var), repr(state_val))
            self.state_binddict[state_i] = cur_binddict
        # go through fsm_obj.fsm and split each OR into its own transition
        new_fsm = {}
        for src_i, transdict in self.fsm_obj.fsm.items():
            new_transdict = {}
            for cond, dst_i in transdict.items():
                self.recurFlattenANDOR(cond)
                self.separateORs(cond, new_transdict, dst_i)
            new_fsm[src_i] = new_transdict
        self.fsm_obj.fsm = new_fsm
        
    # creates a new state that assumes reset values and no other logic
    # no transitions to/fro are created!
    # new_name is scopeChain
    # returns the new state index
    def newState(self, new_name):
        # update self.state_list
        if None in self.state_list:
            new_state_i = self.state_list.index(None)
            self.state_list[new_state_i] = new_name
        else:
            new_state_i = len(self.state_list)
            self.state_list.append(new_name)
        self.fsm_obj.fsm[new_state_i] = {}  # no transitions by default
        # update self.constlist
        # if new state requires an additional bit for state, need to update
        num_states = len(self.state_list)
        width = int(math.ceil(math.log(num_states, 2)))
        if width > int(math.ceil(math.log(num_states-1, 2))):
            for k, v in self.constlist.items():
                if v.width:
##                    v.width = width
                    # hack to allow regenerated code to display " 'dX" instead
                    # specific width
                    v.width = 32
            self.terms[self.state_var].msb.value = width-1
        # same as above hack
##        self.constlist[new_name] = DF.DFEvalValue(new_state_i, width)
        self.constlist[new_name] = DF.DFEvalValue(new_state_i)
        # update self.terms to add a new parameter as well
        self.terms[new_name] = DF.Term(new_name, set(['Parameter']),\
                                       DF.DFEvalValue(31), DF.DFEvalValue(0))
        # new binds for each var
        new_binddict = copy.deepcopy(self.binddict)
        for bindname, bindlist in new_binddict.items():
            for bind in bindlist:
                bind.tree.falsenode = None  # assumes reset!
                                            # not sure what default behaviour is
        self.state_binddict[new_state_i] = new_binddict
        return new_state_i

    # creates a new transition from src to dst with cond
    # src, dst are ScopeChains, cond is a DFOperator object
    def newTransition(self, src, dst, cond):
        src_i = None
        dst_i = None
        if src in self.state_list:
            src_i = self.state_list.index(src)
        if dst in self.state_list:
            dst_i = self.state_list.index(dst)
        if (src_i == None) or (dst_i == None):
            print("Error: src or dst not found in state enum dictionary.")
        self.fsm_obj.fsm[src_i][cond] = dst_i
##        print("Added transition from {} to {}".format(src, dst))
        
    # expects module to be a ScopeChain object or a string if top level
    # creates a new Term and adds it to the termlist
    #   follows same input format as the dataflow.term object
    # also creates and returns a new DFTerminal object for use in dataflows
    def newVar(self, module, name,
               termtype=(), msb=None, lsb=None, lenmsb=None, lenlsb=None):
        var = newScope(module, name)
        # create the Term object and add it to the termlist
        term = DF.Term(var, termtype, msb, lsb, lenmsb, lenlsb)
        self.terms[var] = term
        # additionally create a DFTerminal node for this variable to be used
        # in dataflows
        node = DF.DFTerminal(var)
        return node

    # creates a new wire
    def newWire(self, module, name, msb=None, lsb=None,
                lenmsb=None, lenlsb=None):
        termtype = set(['Wire'])
        return self.newVar(module, name, termtype, msb, lsb, lenmsb, lenlsb)

    # value should be an int or str
    def newIntConst(self, value):
        return DF.DFIntConst(str(value))

    # updates self.binddict according to self.state_binddict
    def updateBinddict(self):
        for var_name, binds in self.binddict.items():
            for bind in binds:
                # TEMPORARY HACK: if assign statement, we assume that we
                # did not modify the logic here
                if bind.parameterinfo != 'assign':
                    # clear old tree data; we rebuild from scratch using state_
                    # check for reset first
                    if self.isReset(bind.tree):
                        rst_branch = bind.tree
                    else:
                        rst_branch = None
                    bind.tree = None
                    for state_i in range(len(self.state_list)):
                        state = self.state_list[state_i]
                        condnode = DF.DFOperator((DF.DFTerminal(self.state_var),
                                                  DF.DFTerminal(state)),
                                                 'Eq')
                        state_bind = self.state_binddict[state_i][var_name][0]
                        if self.isReset(state_bind.tree):
                            truenode = state_bind.tree.falsenode
                        else:
                            truenode = state_bind.tree
                        falsenode = bind.tree
                        bind.tree = DF.DFBranch(condnode, truenode, falsenode)
                    # add reset back in to root of tree if there was one
                    if rst_branch:
                        rst_branch.falsenode = bind.tree
                        bind.tree = rst_branch

    # updates self.state_binddict[src_i] according to new_transdict
    def updateStateDataflow(self, src_i, new_transdict):
        # rebuilds it from scratch using new_transdict
        binddict = self.state_binddict[src_i]
        for state_bind in binddict[self.state_var]:
            if state_bind.tree and self.isReset(state_bind.tree):
                state_bind.tree.falsenode = None
            else:
                state_bind.tree = None
            for cond, dst_i in new_transdict.items():
                dst = self.state_list[dst_i]
##                # change condition DFEvalValue to DFIntConst since pyverilog
##                # is inconsistent with dataflow/fsm representations
##                cond = evalToInt(cond)
                self.addCondToBind(cond, dst, state_bind)      

    ########################################################################
    # TEMPLATES
    ########################################################################
    
    # inserts a one state delay between src and dst states
    # src, dst, name are ScopeChains
    def insDelayState(self, src, dst, name):
        new_state_i = self.newState(name)
        # always go to dst state
        self.newTransition(name, dst, None)
        # modify state_binddicts as well
        state_bindlist = self.state_binddict[new_state_i][self.state_var]
        for bind in state_bindlist:
            if self.isReset(bind.tree):
                bind.tree.falsenode = DF.DFTerminal(dst)
            else:
                bind.tree = DF.DFTerminal(dst)
        # modify all transitions that used to go from src to dst
        src_i = self.state_list.index(src)
        dst_i = self.state_list.index(dst)
        transdict = self.fsm_obj.fsm[src_i]
        new_transdict = copy.deepcopy(transdict)
        state_bindlist = self.state_binddict[src_i][self.state_var]
        for cond, cur_dst_i in transdict.items():
            if cur_dst_i == dst_i:
                new_transdict.pop(cond)
                new_transdict[cond] = new_state_i
                # modify existing state_binddict to reflect this as well
                for bind in state_bindlist:
                    self.replaceDst(bind.tree, dst, name)
        self.fsm_obj.fsm[src_i] = new_transdict

    # inserts a copied state between src and dst states
    # src, dst, name are ScopeChains
    # which state to copy is random
    def insCopyState(self, src, dst, name):
        copy_i = random.randint(0, len(self.state_list)-1)
        new_state_i = self.newState(name)
        # always go to dst state
        self.newTransition(name, dst, None)
        # modify state_binddicts as well
        copy_binddict = self.state_binddict[copy_i]
        for var, bindlist in copy_binddict.items():
            if var == self.state_var:
                state_bindlist = self.state_binddict[new_state_i]\
                                 [self.state_var]
                for bind in state_bindlist:
                    if self.isReset(bind.tree):
                        bind.tree.falsenode = DF.DFTerminal(dst)
                    else:
                        bind.tree = DF.DFTerminal(dst)
            else:
                self.state_binddict[new_state_i][var] = copy.deepcopy(bindlist)
        # modify all transitions that used to go from src to dst
        src_i = self.state_list.index(src)
        dst_i = self.state_list.index(dst)
        transdict = self.fsm_obj.fsm[src_i]
        new_transdict = copy.deepcopy(transdict)
        state_bindlist = self.state_binddict[src_i][self.state_var]
        for cond, cur_dst_i in transdict.items():
            if cur_dst_i == dst_i:
                new_transdict.pop(cond)
                new_transdict[cond] = new_state_i
                # modify existing state_binddict to reflect this as well
                for bind in state_bindlist:
                    self.replaceDst(bind.tree, dst, name)
        self.fsm_obj.fsm[src_i] = new_transdict
        
    # picks num_scramb PIs, and adds Unot (i.e., flips their value) in every
    # such DFTerminal node in statebinds and fsm.
    # IMPORTANT: currently only works for designs where PI is 1-bit
    # use scramblePIBits() instead!
    def scramblePIs(self, num_scramb):
        PIs = self.getPIs()
        # exempt clk
        PIs.remove(self.clk)
        # and reset from scrambling
        if self.rst:
            PIs.remove(self.rst)
        scramb_PIs = random.sample(PIs, num_scramb)
        for src_i, transdict in self.fsm_obj.fsm.items():
            new_transdict = copy.deepcopy(transdict)
            for cond, dst_i in transdict.items():
                self.flipVars(scramb_PIs, cond)
        for state_i, binddict in self.state_binddict.items():
            for var, binds in binddict.items():
                for bind in binds:
                    bind.tree = self.flipVars(scramb_PIs, bind.tree)
        for src_i in self.fsm_obj.fsm.keys():
            for dst_i in self.fsm_obj.fsm.keys():
                for PI in scramb_PIs:
                    bit_i = -1  # dummy value, should not be used
                    target_val = "~"
                    # add PI flip to self.conditions for I/O mapper
                    self.addCondition(src_i, dst_i, PI, bit_i, target_val)

    # recursively adds 'Unot' to any DFTerminal node PI found in the node tree
    def flipVars(self, PIs, node):        
        if isinstance(node, DF.DFTerminal) and (node.name in PIs):
            return self.unotCond(node)
        if isinstance(node, DF.DFPartselect) and \
           isinstance(node.var, DF.DFTerminal) and \
           (node.var.name in PIs):
            return self.unotCond(node)
        if isinstance(node, DF.DFOperator) or isinstance(node, DF.DFConcat):
            # nextnodes is a tuple
            new_nextnodes = []
            for i in range(len(node.nextnodes)):
                new_nextnodes.append(self.flipVars(PIs, node.nextnodes[i]))
            node.nextnodes = tuple(new_nextnodes)
        elif isinstance(node, DF.DFBranch):
            node.condnode = self.flipVars(PIs, node.condnode)
            node.truenode = self.flipVars(PIs, node.truenode)
            node.falsenode = self.flipVars(PIs, node.falsenode)
        return node

    # picks num_scramb bits to flip, and flips those bits accordingly in the
    # fsm object and the state_binddicts. Also updates self.conditions.
    # DEPRECIATED: replaced by scramblePIBits
    def scramblePIBitsOld(self, num_scramb):
        (scramb_bits, scramb_dict) = self.getScrambBits(num_scramb)
        for src_i, transdict in self.fsm_obj.fsm.items():
            new_transdict = copy.deepcopy(transdict)
            for cond, dst_i in transdict.items():
                self.flipBits(scramb_dict, cond)
        for state_i, binddict in self.state_binddict.items():
            for var, binds in binddict.items():
                for bind in binds:
                    bind.tree = self.flipBits(scramb_dict, bind.tree)
        for src_i in self.fsm_obj.fsm.keys():
            for dst_i in self.fsm_obj.fsm.keys():
                for PI, bit_i in scramb_dict.items():
                    target_val = "~"
                    # add PI flip to self.conditions for I/O mapper
                    self.addCondition(src_i, dst_i, PI, bit_i, target_val)

    # recursively checks each node in a tree for DFTerminal and DFPartselects
    # if the node's name/var is one of the vars to flip, replace itself with a
    # DFConcat node that flips the specified bits, concatenating the parts
    def flipBits(self, flip_dict, node):        
        if isinstance(node, DF.DFTerminal) and (node.name in flip_dict):
            PI = node.name
            num_bits = self.getNumBitsOfVar(PI)
            return self.concatFlipBits(flip_dict, PI, num_bits-1, 0)
        if isinstance(node, DF.DFPartselect) and \
           isinstance(node.var, DF.DFTerminal) and \
           (node.var.name in flip_dict):
            PI = node.var.name
            msb = int(node.msb.value)
            lsb = int(node.lsb.value)
            return self.concatFlipBits(flip_dict, PI, msb, lsb)
        if isinstance(node, DF.DFOperator) or isinstance(node, DF.DFConcat):
            # nextnodes is a tuple
            new_nextnodes = []
            for i in range(len(node.nextnodes)):
                new_nextnodes.append(self.flipBits(flip_dict, node.nextnodes[i]))
            node.nextnodes = tuple(new_nextnodes)
        elif isinstance(node, DF.DFBranch):
            node.condnode = self.flipBits(flip_dict, node.condnode)
            node.truenode = self.flipBits(flip_dict, node.truenode)
            node.falsenode = self.flipBits(flip_dict, node.falsenode)
        return node

    # given ints msb and lsb, creates and returns a DFConcat node that strings
    # all the bits together, flipping those specified by flip_dict as necessary.
    def concatFlipBits(self, flip_dict, PI, msb, lsb):
        flip_bits = flip_dict[PI]
        nextnodes = []
        for bit_i in range(msb, lsb-1, -1):
            bit_node = DF.DFPartselect(DF.DFTerminal(PI),
                                       DF.DFIntConst(str(bit_i)),
                                       DF.DFIntConst(str(bit_i)))
            if bit_i in flip_bits:
                bit_node = self.unotCond(bit_node)
            if msb == lsb:  # special case: single bit only. don't make concat
                return bit_node
            nextnodes.append(bit_node)
        new_node = DF.DFConcat(tuple(nextnodes))
        return new_node

    # picks num_scramb bits to flip, and flips those bits accordingly in the
    # fsm object and the state_binddicts. Also updates self.conditions.
    def scramblePIBits(self, num_scramb):
        (scramb_bits, scramb_dict) = self.getScrambBits(num_scramb)
        # create renamed wires for the scrambled versions of the PIs
        scramb_nodes = self.createScrambVars(scramb_dict)
        # rename all references to the scramble PIs to the new versions
        # all state_binddicts and fsm
        for src_i, transdict in self.fsm_obj.fsm.items():
            new_transdict = copy.deepcopy(transdict)
            for cond, dst_i in transdict.items():
                for (scramb, orig) in scramb_nodes:
                    self.replaceVar(cond, scramb.name, orig.name)
        for state_i, binddict in self.state_binddict.items():
            for var, binds in binddict.items():
                for bind in binds:                    
                    for (scramb, orig) in scramb_nodes:
                        bind.tree = self.replaceVar(bind.tree, scramb.name, \
                                                    orig.name)
        # update binddict, state_binddicts for scrambled PIs
        for (scramb, orig) in scramb_nodes:
            PI = orig.name
            num_bits = self.getNumBitsOfVar(PI)
            tree = self.concatFlipBits(scramb_dict, PI, num_bits-1, 0)
            dest = scramb.name
            msb = None
            lsb = None
            ptr = None
            alwaysinfo = None
            parameterinfo = "assign"
            bind = DF.Bind(tree, dest, msb, lsb, ptr, \
                           alwaysinfo, parameterinfo)
            self.binddict[scramb.name] = [bind,]
            for state_i, binddict in self.state_binddict.items():
                bind = DF.Bind(tree, dest, msb, lsb, ptr, \
                               alwaysinfo, parameterinfo)
                binddict[scramb.name] = [bind,]
        # also update self.conditions
        for src_i in self.fsm_obj.fsm.keys():
            for dst_i in self.fsm_obj.fsm.keys():
                for PI, bit_i in scramb_dict.items():
                    target_val = "~"
                    # add PI flip to self.conditions for I/O mapper
                    self.addCondition(src_i, dst_i, PI, bit_i, target_val)
            
    # returns scramb_bits, a 1D list of (scopechain PI, int bit_i) tuples
    # and scramb_dict, a dict sd[PI] = [bit_i s]
    def getScrambBits(self, num_scramb):
        PIs = self.getPIs()
        # exempt clk
        PIs.remove(self.clk)
        # and reset from scrambling
        if self.rst:
            PIs.remove(self.rst)
        all_bits = []
        for PI in PIs:
            num_bits = self.getNumBitsOfVar(PI)
            for bit_i in range(num_bits):
                all_bits.append((PI, bit_i))
        scramb_bits = random.sample(all_bits, num_scramb)
        scramb_dict = {}
        for PI, bit_i in scramb_bits:
            if PI not in scramb_dict:
                scramb_dict[PI] = [bit_i]
            else:
                scramb_dict[PI].append(bit_i)
        return (scramb_bits, scramb_dict)

    # creates a variable (terms) for each PI in scramb_dict that is the
    # scrambled version of the PI.
    # This is var CREATION only, no binddict/fsm/assigns/logic are added.
    # returns a list of DFTerminal nodes for each new var
    def createScrambVars(self, scramb_dict):
        scramb_nodes = []
        for PI in scramb_dict.keys():
            scramb_PI = copy.deepcopy(PI)
            module = pyverilog.utils.scope.ScopeChain(scramb_PI.scopechain[:-1])
            name = scramb_PI.scopechain[-1]
            name.scopename = name.scopename + "_scramb"
            msb = self.terms[PI].msb
            lsb = self.terms[PI].lsb
            lenmsb = self.terms[PI].lenmsb
            lenlsb = self.terms[PI].lenlsb
            scramb_PI_node = self.newWire(module, name, msb, lsb, \
                                          lenmsb, lenlsb)
            scramb_nodes.append((scramb_PI_node, DF.DFTerminal(PI)))
        return scramb_nodes

    # recursively checks each node in a tree for references to one of the
    # scrambled PIs. If found, replaces it with the scrambled version variable.
    # cond is a DFNode tree, scramb and orig are scopechains
    def replaceVar(self, node, scramb, orig):
        if isinstance(node, DF.DFTerminal) and (node.name == orig):
            node.name = scramb
            return node
        if isinstance(node, DF.DFOperator) or isinstance(node, DF.DFConcat):
            # nextnodes is a tuple
            new_nextnodes = []
            for i in range(len(node.nextnodes)):
                new_nextnodes.append(self.replaceVar(node.nextnodes[i],\
                                                     scramb, orig))
            node.nextnodes = tuple(new_nextnodes)
##            # can just use itself recursively, since destructive
##            for child in node.nextnodes:
##                self.replaceVar(child, scramb, orig)
        elif isinstance(node, DF.DFBranch):
            node.condnode = self.replaceVar(node.condnode, scramb, orig)
            node.truenode = self.replaceVar(node.truenode, scramb, orig)
            node.falsenode = self.replaceVar(node.falsenode, scramb, orig)
        return node

    ########################################################################
    # SEQUENTIAL OBFUSCATIONS
    ########################################################################
    
    ########################################################################
    # UNIFORM STATES
    ########################################################################
    # unfinished
    def genUniformStates(self):
        num_states = len(self.fsm_obj.fsm.keys())
        num_state_bits = int(math.ceil(math.log(num_states, 2)))
        for state_i in range(num_states):
            PIs = self.getPIs()
            # get control PIs
##            unused_PIs = 
##            key_PIs = random.sample(PIs, num_state_bits)
################################################################################

    # iteratively splits edges from a given src state, up to num_bits of PIs
    # used, until all next states have the same frequency
    # trans_freqs is a 1D list of next state freqs
    def uniformStates(self, trans_freqs, src, num_bits):
        src_i = self.state_list.index(src)
        # identify dst with most edges
        done = False
        while not done and not self.nextStatesAreUniform(trans_freqs):
            (done, trans_freqs) = self.stepUniformStates(trans_freqs, src_i, \
                                                         num_bits)

    # iteratively splits edges from a given src state, up to num_bits of PIs
    # used, until all next state freqs are non-zero
    # trans_freqs is a 1D list of next state freqs
    def nonZeroStates(self, trans_freqs, src, num_bits):
        src_i = self.state_list.index(src)
        # identify dst with most edges
        done = False
        while not done and not self.nextStatesAreNonZero(trans_freqs):
            (done, trans_freqs) = self.stepFlattenStates(trans_freqs, src_i, \
                                                         num_bits)
        return trans_freqs

    # returns True if the next state freqs (trans_freqs) are all equal
    def nextStatesAreUniform(self, trans_freqs):
        mean = sum(trans_freqs) / len(trans_freqs)
        for elem in trans_freqs:
            if elem != mean:
                return False
        return True

    # returns True if the next state freqs (trans_freqs) are all non-zero
    def nextStatesAreNonZero(self, trans_freqs):
        return not (0 in trans_freqs)

    # one iteration of splitting an edge from most frequent next state to least
    # frequent. checks against num_bits as a constraint as well.
    def stepFlattenStates(self, trans_freqs, src_i, num_bits):
        big_dst_i = trans_freqs.index(max(trans_freqs))
        # identify edge whose size is closest to double the edge surplus to
        # ideal and meets num_bits
        ideal_freq = sum(trans_freqs) / len(trans_freqs)
        big_freq = trans_freqs[big_dst_i]
        surp_freq = big_freq - ideal_freq
        target_edge_size = surp_freq * 2
        transdict = self.fsm_obj.fsm[src_i]
        (best_cond, best_edge_size) = self.getTargetEdge(trans_freqs, transdict,
                                                         big_dst_i,
                                                         target_edge_size)
        avail_bits = self.getAvailBits(best_cond, num_bits)
        if len(avail_bits) == 0:    # no more bits we can use to split
            return (True, trans_freqs)
        [(PI, bit_i)] = random.sample(avail_bits, 1)
        # identify dst with least edges (or closest to deficit?)
        small_dst_i = trans_freqs.index(min(trans_freqs))
        # split edge to 2nd dst
        dst_pool = [small_dst_i]
        cur_cond = best_cond
        dst_i = big_dst_i
        new_transdict = copy.deepcopy(transdict)
        (new_transdict, cur_cond, mod_cond, new_dst_i) = \
            self.splitCond(new_transdict, dst_pool, cur_cond,\
                           PI, bit_i, src_i, dst_i)
        # update fsm
        self.fsm_obj.fsm[src_i] = new_transdict
        # update trans_freqs
        size_change = best_edge_size / 2
        trans_freqs[big_dst_i] -= size_change
        trans_freqs[small_dst_i] += size_change
        # update state dataflow as well
        self.updateStateDataflow(src_i, new_transdict)
        return (False, trans_freqs)        

    # helper for finding the correct edge to split. Selects the edge that is
    # the closest fit to the target edge size, and returns its
    # (cond, edge size)
    def getTargetEdge(self, trans_freqs, transdict, big_dst_i, \
                      target_edge_size):
        best_diff = sum(trans_freqs)    # arbitrarily large as dummy value
        best_cond = transdict.keys()[0] # arbitrary
        best_edge_size = 0
        for cond, dst_i in transdict.items():
            # find edge that goes to big_dst_i with the closest size to
            # target edge size
            if dst_i == big_dst_i:
                cur_edge_size = self.getEdgeSize(cond)
                cur_diff = abs(cur_edge_size - target_edge_size)
                if cur_diff < best_diff:
                    best_diff = cur_diff
                    best_cond = cond
                    best_edge_size = cur_edge_size
        return (best_cond, best_edge_size)
    
    ########################################################################
    # RANDOMIZE TRANSITIONS FROM STATE
    ########################################################################

    # for each unused PI in a given transition, assign a random bit to each pos
    # to generate a key. Incorrect bit leads to random (inclusive of correct)
    # state
    # does this for every transition originating from a state
    def randomizeTransFromState(self, src, num_bits):
        src_i = self.state_list.index(src)
        transdict = self.fsm_obj.fsm[src_i]
        new_transdict = copy.deepcopy(transdict)
        num_edits = 0
        dst_pool = self.fsm_obj.fsm.keys()

        cond_q = Queue.Queue()
        for cond, dst_i in transdict.items():
            if len(self.getAvailBits(cond, num_bits)) > 0:
                cond_q.put((cond, dst_i))
        while not cond_q.empty():
            (cur_cond, dst_i) = cond_q.get()
            avail_bits = self.getAvailBits(cur_cond, num_bits)
            if len(avail_bits) > 0:
                [(PI, bit_i)] = random.sample(avail_bits, 1)
                (new_transdict, cur_cond, mod_cond, new_dst_i) = \
                    self.splitCond(new_transdict, dst_pool, cur_cond,\
                                   PI, bit_i, src_i, dst_i)
                if len(self.getAvailBits(cur_cond, num_bits)) > 0:
                    cond_q.put((cur_cond, dst_i))
                if len(self.getAvailBits(mod_cond, num_bits)) > 0:
                    cond_q.put((mod_cond, new_dst_i))
                # sanity check
                num_edits += 1
##        for cond, dst_i in transdict.items():
##            avail_bits = self.getAvailBits(cond, num_bits)
##            num_obfs_bits = min(num_bits, len(avail_bits))
##            cur_cond = cond
##            for obfs_bit_i in range(num_obfs_bits):
##                (PI, bit_i) = avail_bits[obfs_bit_i]
##                (new_transdict, cur_cond, mod_cond) = \
##                    self.splitCond(new_transdict, dst_pool, cur_cond,\
##                                   PI, bit_i, src_i, dst_i)
##                # sanity check
##                num_edits += 1
        self.fsm_obj.fsm[src_i] = new_transdict
        # update state dataflow as well
        self.updateStateDataflows(src, new_transdict)
        return num_edits

    # gets the available PI bits from a given condition (not used in the cond)
    # now correctly counts available PI bits, even if part of PI is used
    # bit_limit is optional; if bit_limit = 0, no limit is set
    # returns a 1D list of (PI, bit_i) tuples
    def getAvailBits(self, cond, bit_limit=0):
        avail_bits = []
        PIs = self.getPIs()
        total_bits = 0
        for PI in PIs:
            total_bits += self.getNumBitsOfVar(PI)
        PIs.remove(self.clk)
        if self.rst:
            PIs.remove(self.rst)
        for PI in PIs:
            num_avail_bits = self.getNumBitsOfVar(PI)
            for bit_i in range(num_avail_bits):
                avail_bits.append((PI, bit_i))
        avail_bits = self.removeUsedBits(avail_bits, cond)
        if bit_limit:
            used_bits = total_bits - len(avail_bits)
            if used_bits < bit_limit:
                avail_bits = random.sample(avail_bits, bit_limit - used_bits)
            else:
                avail_bits = []
        return avail_bits

    # given a list of tuples [(PI, bit_i), ...] avail_bits, goes through a
    # dataflow tree t and removes any used bits from avail_bits
    # returns avail_bits in the same form
    def removeUsedBits(self, avail_bits, t):
        if t == None:
            return avail_bits
        if isinstance(t, DF.DFPartselect):
            used_bits = range(int(t.lsb.value), int(t.msb.value)+1)
            avail_bits = [i for i in avail_bits if \
                          (i[0] != t.var.name or not i[1] in used_bits)]
            return avail_bits
        if not isinstance(t, DF.DFNotTerminal):
            if isinstance(t, DF.DFTerminal):
                avail_bits = [i for i in avail_bits if i[0] != t.name]
            return avail_bits
        # non terminal cases
        for child in t.children():
            avail_bits = self.removeUsedBits(avail_bits, child)
        return avail_bits

    # given a PI and its bit position, splits a condition in transdict
    # PI[bit_pos] is assigned a random val [0, 1] to go to the original dst
    # random dst is assigned to alternate, new edge
    def splitCond(self, transdict, dst_pool, cur_cond, PI, bit_i, src_i, dst_i):
        target_val = random.randint(0, 1)
        [new_dst_i] = random.sample(dst_pool, 1)
        new_dst = self.state_list[new_dst_i]
##        print("{}[{}] == {}, {}->{}. new dst {}".format(
##            PI, bit_i, target_val, src_i, dst_i, new_dst_i))
        # generate bit_cond
        target_PSNode = DF.DFPartselect(DF.DFTerminal(PI),
                                        DF.DFIntConst(str(bit_i)),
                                        DF.DFIntConst(str(bit_i)))
        if target_val:
            bit_cond = target_PSNode
            not_cond = self.unotCond(bit_cond)
        else:
            bit_cond = DF.DFOperator((target_PSNode,), 'Unot')
            not_cond = target_PSNode
        # add modified correct transition:
        # AND(cur_cond, bit_cond)
##        cur_cond = self.getCond(transdict, dst_i)
        if cur_cond == None:
            new_cond = bit_cond
        else:
            new_cond = self.andNewCond(cur_cond, bit_cond)
        transdict[new_cond] = transdict.pop(cur_cond)
        # complement transition: OR(AND(cur_cond, not_cond), old_cond)
        if cur_cond == None:
            mod_cond = not_cond
        else:
            mod_cond = self.andNewCond(cur_cond, not_cond)
        transdict[mod_cond] = new_dst_i
        # add new bit_cond to self.conditions for I/O mapper
        self.addCondition(src_i, dst_i, PI, bit_i, target_val)
        return (transdict, new_cond, mod_cond, new_dst_i)

    # adds a constraint to self.conditions
    # see class declaration for format
    def addCondition(self, src_i, dst_i, var, bit_i, target_val):
        if (src_i,dst_i) not in self.conditions:
            self.conditions[(src_i,dst_i)] = {}
        if var not in self.conditions[(src_i,dst_i)]:
            self.conditions[(src_i,dst_i)][var] = []
        self.conditions[(src_i,dst_i)][var].append((bit_i,target_val))

    # inputs is a list of (pattern, (src_i,dst_i))
    # each pattern is an input pattern (1 clock cycle), also a dict
    #   where pattern[var in scopechain] = value in string
    def mapInputs(self, inputs):
        for (pattern, (src_i,dst_i)) in inputs:
            if (src_i,dst_i) in self.conditions:
                constrs_dict = self.conditions[(src_i,dst_i)]
                for var, constrs in constrs_dict.items():
                    val = pattern[var]
                    num_bits = len(val)
                    for (bit_pos, new_val) in constrs:
                        val = pattern[var]
                        if new_val == "~":
                            new_val = ""
                            for mod_i in range(len(val)):
                                if val[mod_i] == "0":
                                    new_val += "1"
                                elif val[mod_i] == "1":
                                    new_val += "0"
                                else:
                                    new_val += val[mod_i]
                            pattern[var] = new_val
                        else:
                            # verilog 0 is lsb, need to reverse for python
                            # strings
                            mod_i = num_bits - bit_pos - 1
                            pattern[var] = val[:mod_i] + str(new_val) + \
                                           val[mod_i+1:]
        return inputs
    
    ########################################################################
    # ADD RANDOM TRANSITION
    ########################################################################

    # adds a transition from random src to random dst with a "random" condition
    # the condition is an unused PI and random value
    def addRandTrans(self):
        added = False
        # potential infinite loop! be careful how many times this function is
        # called
        while not added:
            [src_i, dst_i] = random.sample(self.fsm_obj.fsm.keys(), 2)
            src = self.state_list[src_i]
            dst = self.state_list[dst_i]
            added = self.addRandTransSrcDst(src, dst)

    # adds a transition from src to dst with a "random" condition
    # the condition is an unused PI and random value (var != val)
    # src, dst are ScopeChains
    # returns True if successful, False otherwise
    def addRandTransSrcDst(self, src, dst):
        PIs = self.getPIs()
        unused_PIs = self.getUnusedPIs(PIs, src)
        if len(unused_PIs) == 0:
            print("No unused PIs available to add transition from {} to {}".\
                  format(src, dst))
            return False
        target = random.sample(unused_PIs, 1)[0]
        target_val = self.getRandomValue(target)
        # generate condition. new trans takes higher priority than existing
        # i.e. all existing transitions get AND with !(new_cond)
        new_cond = DF.DFOperator((DF.DFTerminal(target),
                                  DF.DFEvalValue(target_val)),
                                 'NotEq')
        # for both modified and original transition dictionaries
        src_i = None
        if src in self.state_list:
            src_i = self.state_list.index(src)
        not_cond = self.notCond(new_cond)
        self.addCondToTransitions(src_i, not_cond)
        self.newTransition(src, dst, new_cond)
        # also update the state dataflow in self.state_binddict
        src_i = self.state_list.index(src)
        state_bind = self.state_binddict[src_i][self.state_var]
        for bind in state_bind:
            self.addCondToBind(new_cond, dst, bind)
        return True
    
    ########################################################################
    # COMMON SEQUENTIAL OBFUSCATION HELPERS
    ########################################################################
    # MISC
    ########################################################################

    # returns the number of bits used in this variable
    def getNumBitsOfVar(self, var):
        var_term = self.terms[var]
        num_bits = int(var_term.msb.value) - int(var_term.lsb.value) + 1
        return num_bits

    # returns a random (unsigned) int value that is representable by the
    # given variable
    def getRandomValue(self, var):
        num_bits = self.getNumBitsOfVar(var)
        return random.randint(0, (2**num_bits)-1)

    # recursively checks for DFBranch nodes where cond is the given cond
    # and the truenode is orig_dst. If found, replaces orig_dst with new_dst
    def replaceDst(self, node, orig_dst, new_dst):
        if isinstance(node, DF.DFBranch) and\
           node.truenode == DF.DFTerminal(orig_dst):
            node.truenode = DF.DFTerminal(new_dst)
        for child in node.children():
            self.replaceDst(child, orig_dst, new_dst)

    ########################################################################
    # COUNTING AND EVALUATION
    ########################################################################

    # given a 2D list all_trans_freqs, returns the number of non-zero entries
    # counts the number of (src,dst) connections
    def countConnects(self, all_trans_freqs):
        freqs = np.array(all_trans_freqs)
        num_connects = sum(sum(freqs != 0))
        return num_connects

    # counts the number of edges that this condition is responsible for
    def getEdgeSize(self, cond):
        avail_bits = self.getAvailBits(cond)
        num_unused_bits = len(avail_bits)
        return 2 ** num_unused_bits

    # counts the number of edges (transitions) in the current graph (fsm)
    def countEdges(self, fsm):
        total_edges = 0
        for src_i, transdict in fsm.items():
            state_edges = len(transdict.keys())
            total_edges += state_edges
        return total_edges

    # counts the number of subFSMs from a given fsm
    # this assumes that graphs with unreachable states but same edges as another
    # graph are DIFFERENT, so counts those separately.
    def countSubFSMs(self, fsm):
        total = 0
        num_states = len(fsm.keys())
        for i in range(2**num_states):
            state_code = bin(i).lstrip('0b').zfill(num_states)
            print(state_code)
            new_fsm = copy.deepcopy(fsm)
            for state_i in range(len(state_code)):
                incl = state_code[state_i]
                if incl == '0':
                    new_fsm = self.removeStateFromFSM(new_fsm, state_i)
            # count number of edges in the subFSM
            edges = self.countEdges(new_fsm)
            subFSMs = 2**edges
            total += subFSMs
            print("{}, {}".format(edges, subFSMs))
            print("")
        return total
            
    # removes a given state (int, not scopechain) from a fsm
    # does NOT alter any dataflows, state_ or overall. state variable is not
    # updated to reflect missing states. for use in counting subgraphs only!
    def removeStateFromFSM(self, fsm, state_i):
        # remove this state, its transitions, and all transitions
        # that lead to this state
        fsm.pop(state_i)
        for src_i, transdict in fsm.items():
            new_transdict = copy.deepcopy(transdict)
            for cond, dst_i in transdict.items():
                if dst_i == state_i:
                    new_transdict.pop(cond)
            fsm[src_i] = new_transdict
        return fsm
        
    # populates self.trans_freqs, a 2D list of src->dst mapping. each entry
    # is number of input patterns (or edges) from src to dst
    # returns the new self.trans_freqs and the number of PIs
    def getTransFreqs(self):
        num_states = len(self.fsm_obj.fsm.keys())
        self.trans_freqs = []
        for src_i in range(num_states):
            self.trans_freqs.append([0] * num_states)
        PIs = self.getPIs()
        PIs.remove(self.clk)
        if self.rst:
            PIs.remove(self.rst)
        PIs = list(PIs)
        num_PIs = len(PIs)
        PI_len_list = []
        for PI in PIs:
            PI_len = self.getNumBitsOfVar(PI)
            PI_len_list.append(PI_len)
        code_len = sum(PI_len_list)
        for i in range(2**code_len):
            cur_in = {}
            code = bin(i).lstrip('0b').zfill(code_len)
            code_i = 0
            for PI_i in range(len(PI_len_list)):
                PI = PIs[PI_i]
                PI_len = PI_len_list[PI_i]
                val = code[code_i:code_i + PI_len]
                cur_in[PI] = val
                code_i += PI_len
            for src_i, transdict in self.fsm_obj.fsm.items():
                dst_i = self.getDestination(transdict, cur_in)
                self.trans_freqs[src_i][dst_i] += 1
        return (self.trans_freqs, num_PIs)

    # normalizes the trans_freqs 2D list against the number of PIs used
    # trans_freqs should be a square. returns the new normalized trans_freqs
    def normalizeTransFreqs(self, trans_freqs, num_PIs):
        num_states = len(trans_freqs)
        for i in range(num_states):
            for j in range(num_states):
                trans_freqs[i][j] = float(trans_freqs[i][j]) / (2 ** num_PIs)
        return trans_freqs

    # returns the score of the closest fit NSF in the candidate distribution
    # to the original distribution
    # orig and candidate are 1D lists (NSFs). if they are not of equal size,
    # then candidate must be larger, and only permutations of the same size as
    # orig are considered
    def scoreClosestNSF(self, orig, candidate):
        scores = []
        num_states = len(orig)
        for cur_freqs in list(itertools.permutations(candidate, num_states)):
            cur_score = self.getEarthMoversDistance(orig, cur_freqs)
            scores.append(cur_score)
        return min(scores)

    # for every pairwise comparison between each original FSM state's NSFs and
    # every obfuscated FSM state's NSFs, obtain the minimum EMD score
    # tracks the scores of all comparisons in all_scores, but returns the
    # min in the table
    # orig_table and cand_table are both square 2D lists, each row is a 1D list
    # NSF for that state
    def scoreAllNSF(self, orig_table, cand_table):
        num_orig_states = len(orig_table)
        num_cand_states = len(cand_table)
        all_scores = []
        for i in range(num_orig_states):
            all_scores.append([0] * num_cand_states)
        for i in range(num_orig_states):
            orig_state_NSF = orig_table[i]
            for j in range(num_cand_states):
                cand_state_NSF = cand_table[j]
                cur_score = self.scoreClosestNSF(orig_state_NSF, cand_state_NSF)
                all_scores[i][j] = cur_score
        best_min_score = num_orig_states
        for i in range(num_orig_states):
            cur_min_score = min(all_scores[i])
            if cur_min_score < best_min_score:
                best_min_score = cur_min_score
        return best_min_score

    # calculates the Earth Mover's Distance between two distributions A and B
    # A and B are 1D lists of equal size
    def getEarthMoversDistance(self, A, B):
        emd = 0
        emd_list = []
        for i in range(len(A)):
            emd = A[i] + emd - B[i]
            emd_list.append(emd)
        return sum(map(abs, emd_list))

    ########################################################################
    # CLASSIFIER METHODS
    ########################################################################
    
    # generate training data for per-state classifiers
    # features are PIs, next state, (TBD: outputs)
    # label is 1 for meaningful (correct), 0 for non-meaningful (not in design)
    def generateStateData(self, out_dir):
        PIs = self.getPIs()
        PIs.remove(self.clk)
        if self.rst:
            PIs.remove(self.rst)
        PIs = list(PIs)
        PIs = sorted(PIs, key=lambda x:str(x))
        num_PIs = len(PIs)
        for src_i, transdict in self.fsm_obj.fsm.items():
            data = []
            titles = []
            for PI in PIs:
                titles.append(PI)
            titles.append("next_state")
            titles.append("label")
            data.append(titles)
            for i in range(2**num_PIs):
                cur_in = {}
                code = bin(i).lstrip('0b').zfill(num_PIs)
                for PI_i in range(len(code)):
                    PI = PIs[PI_i]
                    val = code[PI_i]
                    cur_in[PI] = val
                dst_i = self.getDestination(transdict, cur_in)
                # form sample
                samp1 = []
                for PI in PIs:
                    samp1.append(cur_in[PI])
                # generate duplicate for non-meaningful version of sample
                samp0 = copy.deepcopy(samp1)
                # fill out next state (TODO: output as well) and label
                samp1.append(dst_i)
                samp1.append(1)
                dst_pool = set(self.fsm_obj.fsm.keys())
                dst_pool.remove(dst_i)
                samp0.append(random.sample(dst_pool,1)[0])
                samp0.append(0)
                data.append(samp1)
                data.append(samp0)
            # write data to file
            out_path = out_dir.rstrip("/") + "/inout_s{}.csv".format(src_i)
            with open(out_path, 'wb') as csv_out:
                writer = csv.writer(csv_out, delimiter=',')
                for samp in data:
                    writer.writerow(samp)

    # given a data_dir, trains a RandomForestClassifier (sklearn) for each state
    # in the current FSM. Uses the training data in data_dir
    # expects each state's training data to be named "inout_s{}.csv"
    def trainClassifiers(self, data_dir):
        num_states = len(self.fsm_obj.fsm.keys())
        self.classifiers = [None] * num_states
        for src_i in sorted(self.fsm_obj.fsm.keys()):
            # get training data
            in_path = data_dir.rstrip("/") + "/inout_s{}.csv".format(src_i)
            data = []
            data = np.genfromtxt(in_path, dtype=int, delimiter=',', \
                                 skip_header=1)
            XTrain = data[:,:-1]
            YTrain = data[:,-1]
            # train classifier
            classifier = RandomForestClassifier()
            classifier.fit(XTrain, YTrain)
            self.classifiers[src_i] = classifier

    def evalCurrentFSM(self):
        scores = [0] * len(self.fsm_obj.fsm.keys())
        PIs = self.getPIs()
        PIs.remove(self.clk)
        if self.rst:
            PIs.remove(self.rst)
        PIs = list(PIs)
        PIs = sorted(PIs, key=lambda x:str(x))
        num_PIs = len(PIs)
        for src_i, transdict in self.fsm_obj.fsm.items():
            clf = self.classifiers[src_i]
            # generate test/validation data
            num_samp = 2**num_PIs
            num_feat = num_PIs + 1  # 1 for next state
            data = np.zeros(shape=(num_samp, num_feat))
            for i in range(2**num_PIs):
                cur_in = {}
                code = bin(i).lstrip('0b').zfill(num_PIs)
                for PI_i in range(len(code)):
                    PI = PIs[PI_i]
                    val = code[PI_i]
                    cur_in[PI] = val
                dst_i = self.getDestination(transdict, cur_in)
                # form sample
                samp = []
                for PI in PIs:
                    samp.append(cur_in[PI])
                samp.append(dst_i)
                data[i] = np.array(samp)
            # use classifier
            preds = clf.predict(data)
            score = float(sum(preds)) / len(preds)
            scores[src_i] = score
        return scores

    ########################################################################
    # PRIMARY INPUT FUNCTIONS
    ########################################################################

    # returns a set of ScopeChains that are the variables for each primary
    # input to the design
    def getPIs(self):
        PIs = set()
        for name, term in self.terms.items():
            if 'Input' in term.termtype:
                PIs.add(name)
        return PIs

    # returns a set of ScopeChains that are the variables for each port
    # in the design
    def getPorts(self):
        ports = set()
        for name, term in self.terms.items():
            if 'Input' in term.termtype:
                ports.add(name)
            if 'Output' in term.termtype:
                ports.add(name)
            if 'Inout' in term.termtype:
                ports.add(name)
        return ports

    # returns a set of PIs that are not used in the particular state src
    # this is a pessimistic grab: it only selects PIs that do not appear
    # at all in the dataflows, even if they have no overall impact on operation
    def getUnusedPIs(self, PIs, src):
        # first remove clk from the PIs, since it is a special case that doesn't
        # naturally appear in dataflows anyway
        PIs.remove(self.clk)
        # and reset
        if self.rst:
            PIs.remove(self.rst)
        unused_PIs = copy.deepcopy(PIs)
        src_i = self.state_list.index(src)
        binddict = self.state_binddict[src_i]
        for PI in PIs:
            # check each bind in the src state to see if this PI is used in it
            for var, bindlist in binddict.items():
                for bind in bindlist:
                    if bindContainsVar(bind, PI):
                        unused_PIs.discard(PI)
        return unused_PIs

    # returns a set of PIs that are not used in a particular condition tree
    def getUnusedPIsFromCond(self, PIs, cond):
        # first remove clk from the PIs, since it is a special case that doesn't
        # naturally appear in dataflows anyway
        PIs.remove(self.clk)
        # and reset
        if self.rst:
            PIs.remove(self.rst)
        unused_PIs = copy.deepcopy(PIs)
        for PI in PIs:
            if treeContainsVar(cond, PI):
                unused_PIs.discard(PI)
        return unused_PIs

    # returns a set of PIs that are used in a particular condition tree
    def getUsedPIsFromCond(self, PIs, cond):
        # first remove clk from the PIs, since it is a special case that doesn't
        # naturally appear in dataflows anyway
        PIs.remove(self.clk)
        # and reset
        if self.rst:
            PIs.remove(self.rst)
        used_PIs = set()
        for PI in PIs:
            if treeContainsVar(cond, PI):
                used_PIs.add(PI)
        return used_PIs
        

    ########################################################################
    # CONDITION MANIPULATION
    ########################################################################

    # evaluates a condition given an expression expr
    # cond is a tree of DF nodes, expr is a dict: [var in scopeChain] to str
    # returns (True/False, val). val is used when recursively going through
    # the cond tree
    def evalCond(self, node, expr):
        if node == None:    # special: cond is None, so by def it is always true
            return (True, None)
        if isinstance(node, DF.DFIntConst):
            val = bin(int(node.value))[2:]
            return ('1' in val, val)
        if isinstance(node, DF.DFEvalValue):
            val = bin(node.value)[2:]
            return ('1' in val, val)
        if isinstance(node, DF.DFTerminal):
            name = node.name
            if (name not in expr) and (name in self.binddict):
                interm_bind = self.binddict[node.name][0]
                (interm_val_bool, interm_val) = self.evalCond(interm_bind.tree,\
                                                              expr)
                expr[node.name] = interm_val
            val = expr[node.name]
            return ('1' in val, val)
        if isinstance(node, DF.DFPartselect):
            name = node.var.name
            if (name not in expr) and (name in self.binddict):
                interm_bind = self.binddict[name][0]
                (interm_val_bool, interm_val) = self.evalCond(interm_bind.tree,\
                                                              expr)
                expr[name] = interm_val
            val = expr[name]
            num_bits = self.getNumBitsOfVar(name)
            msb = int(node.msb.value)
            lsb = int(node.lsb.value)
            # include lsb
            val = val[num_bits - msb - 1 : num_bits - lsb]
            return ('1' in val, val)
        if isinstance(node, DF.DFConcat):
            val = ""
            for child in node.nextnodes:
                val += self.evalCond(child, expr)[1]
            return ('1' in val, val)
        if isinstance(node, DF.DFOperator):
            if node.operator == 'GreaterThan':
                left = self.evalCond(node.nextnodes[0], expr)[1]
                right = self.evalCond(node.nextnodes[1], expr)[1]
                # this assumes unsigned!
                return (int(left) > int(right), None)
            if node.operator == 'Unot':
                val = self.evalCond(node.nextnodes[0], expr)[1]
                new_val = ""
                for c in val:
                    if c == '1':
                        new_val += '0'
                    else:
                        new_val += '1'
                return ('1' in new_val, new_val)
            if node.operator == 'Ulnot':
                (tf, val) = self.evalCond(node.nextnodes[0], expr)
                return (not tf, val)
            if node.operator == 'Land':
                (L_tf, L_val) = self.evalCond(node.nextnodes[0], expr)
                (R_tf, R_val) = self.evalCond(node.nextnodes[1], expr)
                return (L_tf and R_tf, None)
            if node.operator == 'Lor':
                (L_tf, L_val) = self.evalCond(node.nextnodes[0], expr)
                (R_tf, R_val) = self.evalCond(node.nextnodes[1], expr)
                return (L_tf or R_tf, None)
        # shouldn't get here
##        print("Reached undefined/unimplemented node")
        return (None, None)
    # PROBLEM: evalCond doesn't work when we don't know intermediate variables
    # e.g. count in add_serial

    # given an expression expr, checks the conditions of each transition in
    # transdict for a match.
    # returns state dst_i if found, None otherwise
    def getDestination(self, transdict, expr):
        for cond, dst_i in transdict.items():
            (tf, eval_val) = self.evalCond(cond, expr)
            if tf:
                return dst_i
        return None
    
    # adds a new condition clause to all existing transitions
    # originating from state src (specified by src_i, which is int)
    # i.e. all existing transitions get AND with new_cond
    def addCondToTransitions(self, src_i, new_cond):
        transdict = self.fsm_obj.fsm[src_i]
        new_transdict = {}
        for cond, dst in transdict.items():
            new_key = self.andNewCond(cond, new_cond)
            new_transdict[new_key] = dst
        self.fsm_obj.fsm[src_i] = new_transdict

    # CURRENTLY UNUSED
    # adds a new condition clause to ONE transition, specified by
    # transdict and cond
    def addCondToTransition(self, transdict, cond, new_cond):
        new_cond = self.andNewCond(cond, new_cond)
        transdict[new_cond] = transdict.pop(cond)

    # ANDs a given condition with a new condition
    def andNewCond(self, cond, new_cond):
        if cond:
            final_cond = DF.DFOperator((cond, new_cond), 'Land')
        else:
            final_cond = new_cond
        return final_cond

    # ORs a given condition with a new condition
    def orNewCond(self, cond, new_cond):
        if cond:
            final_cond = DF.DFOperator((cond, new_cond), 'Lor')
        else:
            final_cond = new_cond
        return final_cond

    # NOTs a condition
    def notCond(self, cond):
        return DF.DFOperator((cond,), 'Ulnot')

    # UNOTs a condition (bit-not)
    def unotCond(self, cond):
        return DF.DFOperator((cond,), 'Unot')

    # performs LAND distribute across one LOR node left and
    # some other node right
    def distrAND2(self, left, right):
        a1 = self.andNewCond(left.nextnodes[0],right)
        a2 = self.andNewCond(left.nextnodes[1],right)
        out = self.orNewCond(a1, a2)
        return out

    # performs LAND distribute across two LOR nodes left and right
    def distrAND4(self, left, right):
        a1 = self.andNewCond(left.nextnodes[0],right.nextnodes[0])
        a2 = self.andNewCond(left.nextnodes[0],right.nextnodes[1])
        a3 = self.andNewCond(left.nextnodes[1],right.nextnodes[0])
        a4 = self.andNewCond(left.nextnodes[1],right.nextnodes[1])
        o1 = self.orNewCond(a1, a2)
        o2 = self.orNewCond(a3, a4)
        out = self.orNewCond(o1, o2)
        return out
    
    # returns true if a node is a Land node
    def isLand(self, node):
        return isinstance(node, DF.DFOperator) and node.operator == 'Land'

    # returns true if a node is a Lor node
    def isLor(self, node):
        return isinstance(node, DF.DFOperator) and node.operator == 'Lor'

    # returns true if node is the branch of a reset (either reset or
    # unot(reset) for negedge
    def isReset(self, node):
        if isinstance(node, DF.DFBranch):
            if node.condnode == DF.DFTerminal(self.rst):
                return True
            elif isinstance(node.condnode, DF.DFOperator) and\
                 (node.condnode.operator == 'Unot' or\
                  node.condnode.operator == 'Ulnot') and\
                  node.condnode.nextnodes[0] == DF.DFTerminal(self.rst):
                return True
        else:
            return False

    # checks if a node's children has an AND and at least one of the AND's
    # children is an OR. distributes the AND over the OR if found.
    # destructively modifies node
    def flattenANDOR(self, node):
        if not isinstance(node, DF.DFOperator):
            return node
        for i in range(len(node.nextnodes)):
            child = node.nextnodes[i]
            if self.isLand(child):
                left = child.nextnodes[0]
                right = child.nextnodes[1]
                if self.isLor(left):
                    if self.isLor(right):
                        node.nextnodes[i] = self.distrAND4(left, right)
                    else:
                        node.nextnodes[i] = self.distrAND2(left, right)
                elif self.isLor(right):
                    # left is not Lor
                    node.nextnodes[i] = self.distrAND2(right, left)
        return node

    # recursively applies flattenANDOR on a given node and its children
    # destructively modifies node
    def recurFlattenANDOR(self, node):
        if not node:
            return
        if len(node.children()) == 0:
            return
        self.flattenANDOR(node)
        for child in node.children():
            self.recurFlattenANDOR(child)

    # flattens a tree of Lor nodes for a transdict
    # recursively modifies transdict with the new entries
    def separateORs(self, node, transdict, dst_i):
        if not self.isLor(node):
            transdict[node] = dst_i
            return
        self.separateORs(node.nextnodes[0], transdict, dst_i)
        self.separateORs(node.nextnodes[1], transdict, dst_i)

    # adds a new branch to the root of the bind. If cond is true, goes to dst,
    # otherwise to the rest of the tree
    # replaces the root of the bind unless the root is reset, then new branch
    # takes second priority
    # if cond is None, then don't create a branch at all: cond is "always true"
    # so always go to dst
    def addCondToBind(self, cond, dst, bind):
        dst_node = DF.DFTerminal(dst)
        new_branch = DF.DFBranch(cond, dst_node, None)
        if self.isReset(bind.tree):
            if cond:
                new_branch.falsenode = bind.tree.falsenode
            else:
                new_branch = dst_node
            bind.tree.falsenode = new_branch
        else:
            if cond:
                new_branch.falsenode = bind.tree
            else:
                new_branch = dst_node
            bind.tree = new_branch

    # returns true if there is a transition in transdict to dst_i
    # dst_i is int
    def hasTrans(self, transdict, dst_i):
        for cond, cur_dst_i in transdict.items():
            if cur_dst_i == dst_i:
                return True
        return False

    # returns the condition of the transition in transdict to dst_i
    # dst_i is int
    def getCond(self, transdict, dst_i):
        for cond, cur_dst_i in transdict.items():
            if cur_dst_i == dst_i:
                return cond
        # should not get here unless getCond was called by mistake
        print("Error: getCond was called when no transition to dst_i exists.")
        return None

    ########################################################################
    # TOCODE
    ########################################################################
    def toCode(self, top_module, file_dest):
        # first make sure binddict is updated
        self.updateBinddict()
        ports = self.getPorts()
        head = "module " + top_module + "("
        for port in ports:
            flatname = port.scopechain[-1].tocode()
            head += flatname + ","
        if head[-1] == ",":
            head = head[:-1]
        head += ");\n"
        # declarations
        declares = ""
        for name, term in self.terms.items():
            declares += self.termToCode(term)
        # main body
        assigns = ""
        body = ""
        for var_name, binds in self.binddict.items():
            for bind in binds:
                bindcode = bind.tocode()
                # simplifyCode is BENCHMARK SPECIFIC
                bindcode = self.simplifyCode(bindcode, top_module)
                if bind.parameterinfo == 'assign':
                    assigns += bindcode
                elif bind.parameterinfo != 'parameter':
                    body += bindcode
        # endmodule
        foot = "endmodule"
        out = head + declares + assigns + body + foot
        f = open(file_dest, 'w')
        f.write(out)
        f.close()
    
    # converts a Term object to a declaration piece of code
    def termToCode(self, term):
        out = ""
        for label in term.termtype:
            if label.lower() == "rename":
                out += "wire "
            else:
                out += label.lower() + " "
        out += "[" + str(term.msb.value) + ":" + str(term.lsb.value) + "]"
        out += " " + term.name.scopechain[-1].tocode()
        if term.name in self.constlist:
            val = self.constlist[term.name]
            out += " = " + val.tocode()
        out += ";\n"
        return out

    # NOTE: this makes BENCHMARK specific optimizations to the code to make it
    # shorter (except for top module, which is mandatory for all)
    def simplifyCode(self, code, top_module):
        code = code.replace(top_module+'_', '')
##        # SHOULD BE OK TO REPLACE >'d0 WITH NOTHING
##        # ONLY FOR SOME CODE
##        code = code.replace(">'d0", "")
        # following section for dma_rrarb only
        if top_module == "dma_rrarb":
            code = code.replace("!","~")
            code = code.replace("[0]","")
            code = code.replace("&&","&")
            code = code.replace("||","|")
##        code = code.replace("(next_ch)","next_ch")
##        code = code.replace("(~next_ch)","~next_ch")
##        for i in range(8):
##            var = "vld_req" + str(i)
##            code = code.replace("("+var+")",var)
##            code = code.replace("(~"+var+")","~"+var)
        return code

########################################################################
# MISC FUNCTIONS
########################################################################

# helper function to convert strings to scope chain objects
# module can be ScopeChain or string (only if top module)
def newScope(module, name):
    var = pyverilog.utils.scope.ScopeChain()
    if not isinstance(module, pyverilog.utils.scope.ScopeChain) \
       and isinstance(module, str):
        module_scopeL = pyverilog.utils.scope.ScopeLabel(module, 'module')
    elif isinstance(module, pyverilog.utils.scope.ScopeChain):
        module_scopeL = module
    else:
        module_scopeL = None
    var += module_scopeL
    if isinstance(name, pyverilog.utils.scope.ScopeLabel):
        var += name
    else:
        var += pyverilog.utils.scope.ScopeLabel(name, 'signal')
    return var

# returns true if a given bind contains a variable in its dataflow tree
# false otherwise
def bindContainsVar(bind, var):
    return treeContainsVar(bind.tree, var)

# returns true if a given tree contains a variable, false otherwise
# recursively explores the tree
def treeContainsVar(t, var):
    if t == None:
        return False
    if not isinstance(t, DF.DFNotTerminal):
        return (isinstance(t, DF.DFTerminal) and (t.name == var))
    # non terminal cases
    # nextnodes: DFOperator, DFConcat, DFSyscall
    # var: DFPartselect, DFPointer
    # condnode: DFBranch
    # nextnode: DFDelay
    for child in t.children():
        if treeContainsVar(child, var):
            return True
    return False

# returns true if a given bind's tree starts with a DFBranch with condition rst
# bind is a bind object, rst is a scopeChain
def bindHasReset(bind, rst):
    t = bind.tree
    if not isinstance(t, DF.DFBranch):
        return False
    if not isinstance(t.condnode, DF.DFTerminal):
        return False
    return t.condnode.name == rst


# UNFINISHED
# changes all DFEvalValue to DFIntConst due to pyverilog inconsistency
# returns the modified condition tree (DFBranch)
def evalToInt(cond):
    new_cond = copy.deepcopy(cond)
    if isinstance(new_cond, DF.DFNotTerminal):
        for child in new_cond.children:
            if isinstance(child, DF.DFEvalValue) and (type(new_cond.value) == int):
                return

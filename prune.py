import pyverilog

# wrapper of main prune function, this checks the root node itself.
def pruneBind(bind, state_var, state_val):
    # check self in case root node is a DFBranch
    node = bind.tree
    if isinstance(node, pyverilog.dataflow.dataflow.DFBranch):
        prune = checkBranch(bind.tree, state_var, state_val)
        while prune != -1:
            if prune == 1:      # always true
                bind.tree = node.truenode
            elif prune == 0:    # always false
                bind.tree = node.falsenode
            node = bind.tree
            prune = checkBranch(node, state_var, state_val)
    # call recursively on children
    pruneBindTree(bind.tree, state_var, state_val)

# takes a Bind object tree, prunes it of branches that involve a state by
# assuming the state will be of a constant value.
def pruneBindTree(node, state_var, state_val):
    # DFS (easier than BFS) through the tree
    # at each node, go through children
    # if a child is type DFBranch and condnode is Eq (is there less than or mroe?)
    # and its variable is [state_var], then
    # if else to change pointers as appropriate

    # base cases:
    # node is terminal node
    if not isinstance(node, pyverilog.dataflow.dataflow.DFNotTerminal):
        return
    # check if its children are valid branch nodes to prune
    # nextnodes: DFOperator, DFConcat, DFSyscall
    if isinstance(node, pyverilog.dataflow.dataflow.DFOperator) or\
       isinstance(node, pyverilog.dataflow.dataflow.DFConcat) or\
       isinstance(node, pyverilog.dataflow.dataflow.DFSyscall):
        for node_i in range(len(node.nextnodes)):
            child = node.nextnodes[node_i]
            prune = checkBranch(child, state_var, state_val)
            while prune != -1:
                if prune == 1:      # always true
                    node.nextnodes[node_i] = child.truenode
                elif prune == 0:    # always false
                    node.nextnodes[node_i] = child.falsenode
                child = node.nextnodes[node_i]
                prune = checkBranch(child, state_var, state_val)
    # others: DFBranch, DFDelay
    elif isinstance(node, pyverilog.dataflow.dataflow.DFBranch):
        child = node.condnode
        prune = checkBranch(child, state_var, state_val)
        while prune != -1:
            if prune == 1:      # always true
                node.condnode = child.truenode
            elif prune == 0:    # always false
                node.condnode = child.falsenode
            child = node.condnode
            prune = checkBranch(child, state_var, state_val)
        child = node.truenode
        prune = checkBranch(child, state_var, state_val)
        while prune != -1:
            if prune == 1:      # always true
                node.truenode = child.truenode
            elif prune == 0:    # always false
                node.truenode = child.falsenode
            child = node.truenode
            prune = checkBranch(child, state_var, state_val)
        child = node.falsenode
        prune = checkBranch(child, state_var, state_val)
        while prune != -1:
            if prune == 1:      # always true
                node.falsenode = child.truenode
            elif prune == 0:    # always false
                node.falsenode = child.falsenode
            child = node.falsenode
            prune = checkBranch(child, state_var, state_val)
    elif isinstance(node, pyverilog.dataflow.dataflow.DFDelay):
        child = node.nextnode
        prune = checkBranch(child, state_var, state_val)
        while prune != -1:
            if prune == 1:      # always true
                node.nextnode = child.truenode
            elif prune == 0:    # always false
                node.nextnode = child.falsenode
            child = node.nextnode
            prune = checkBranch(child, state_var, state_val)

    # recursive case
    for child in node.children():
        pruneBindTree(child, state_var, state_val)

# checks a branch node to see if its condition node involves the state_var
# and that the condition is equal to the state_val
# returns -1 if not a valid node
# 1 if the condition is state_var Eq state_val
# 0 otherwise
def checkBranch(node, state_var, state_val):
    # basic check
    if not isinstance(node, pyverilog.dataflow.dataflow.DFBranch):
##        print("Error: checkBranch called on non-branch node")
        return -1
    # real checks
    cn = node.condnode
    if not isinstance(cn, pyverilog.dataflow.dataflow.DFOperator):
        return -1
    if cn.operator != 'Eq':
        return -1
    # node.condnode.nextnodes is a list of 2 nodes. check if one is state_var
    # and the other is state_val
    nn = cn.nextnodes
    if len(nn) != 2:
        print("Error: Eq node.nextnodes does not have 2 elements.")
        return -1
    if ((repr(nn[0]) == state_var) or (repr(nn[1]) == state_var)):
        if ((repr(nn[0]) == state_val) or (repr(nn[1]) == state_val)):
            return 1
        else:
            return 0
    else:
        return -1

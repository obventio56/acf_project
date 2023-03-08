import pickle

def add_bool_arg(parser, name, default=False):
    """
    Add an bool argument to the program
    """
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--' + name, dest=name, action='store_true')
    group.add_argument('--no-' + name, dest=name, action='store_false')
    parser.set_defaults(**{name:default})

def load_trace(fname, sample, sample_rate):
    """
    Load dumped trace generated from preprocess.py
    """
    with open(fname, "rb") as f:
        fiveTuple_list = pickle.load(f)
        if sample:
            sample_sz = int(sample_rate * len(fiveTuple_list))
            return fiveTuple_list[:sample_sz]
        else:
            return fiveTuple_list
    raise Exception("Trace not exists")

def get_trace_stats(fiveTuple_list):
    """
    Get #flows, #pkts from the trace
    """
    st = set()
    for fiveTuple in fiveTuple_list:
        st.add(fiveTuple)
    n_flows = len(st)
    n_pkts = len(fiveTuple_list)
    return n_flows, n_pkts
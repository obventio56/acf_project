"""
Run ACF data structure on CAIDA traces
"""

import argparse
import pickle
import threading

def load_trace(fname):
    """
    Load dumped trace generated from preprocess.py
    """
    with open(fname, "rb") as f:
        fiveTuple_list = pickle.load(f)
        return fiveTuple_list
    raise Exception("Trace not exists")

def get_trace_stats(trace):
    """
    Get #flows, #pkts from the trace
    """
    st = set()
    for fiveTuple in fiveTuple_list:
        st.add(fiveTuple)
    n_flows = len(st)
    n_pkts = len(trace)
    return n_flows, n_pkts

def run_thread(tid, fiveTuple_list, ratio, n_flows, res_map, res_map_lock):
    fp_rate = 0.0

    # First, let's calculate the number of flows for set A and set S
    S_flows = int(n_flows / (1 + ratio))
    A_flows = n_flows - S_flows

    

    with res_map_lock:
        res_map[ratio] = fp_rate
    print("[Thread {}] ratio={} finished".format(tid, ratio))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ACF data structure on CAIDA traces")
    parser.add_argument('input_trace', type=str, help="input CAIDA trace file")
    args = parser.parse_args()

    fiveTuple_list = load_trace(args.input_trace)
    n_flows, n_pkts = get_trace_stats(fiveTuple_list)


    ratio_list = [i for i in range(1, 6)] + [i * 10 for i in range(1, 11)]
    res_map_lock = threading.Lock()
    res_map = dict()
    # Parallel between each ratio
    thread_list = [threading.Thread(target=run_thread, 
                   args=(tid, fiveTuple_list, ratio, n_flows, res_map, res_map_lock)) \
                   for tid, ratio in enumerate(ratio_list)]
    for thread in thread_list:
        thread.start()
    for thread in thread_list:
        thread.join()

    print(res_map)


    
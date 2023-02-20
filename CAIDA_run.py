"""
Run ACF data structure on CAIDA traces
"""

import argparse
import pickle
import threading
from tqdm import tqdm

from acf_firewall import ACF

def load_trace(fname, sample):
    """
    Load dumped trace generated from preprocess.py
    """
    with open(fname, "rb") as f:
        fiveTuple_list = pickle.load(f)
        if sample:
            sample_sz = 0.01 * len(fiveTuple_list)
            return fiveTuple_list[:sample_sz]
        else:
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
    print("[Thread {}] ratio={} started".format(tid, ratio))
    fp_rate = 0.0
    FP = 0
    TN = 0

    # First, let's calculate the number of flows 
    # for set A and set S
    S_flows = int(n_flows / (1 + ratio))
    A_flows = n_flows - S_flows

    # Based on ACF paper, ACF reaches the 
    # 95% load when it is filled
    acf = ACF(b=int(S_flows / 0.95), c=4)
    st = set()
    for fiveTuple in tqdm(fiveTuple_list, desc="[Thread {}]".format(tid)):
        # TODO: It seems hash_with_offset requires input to be integer
        # So we convert the fiveTuple back
        fiveTuple = int.from_bytes(fiveTuple, byteorder="little")
        if len(st) <= S_flows:
            if fiveTuple not in st:
                acf.insert(fiveTuple)
            else:
                st.add(fiveTuple)
            pass
        else:
            # The remaining are used to 
            # check false positive rate 
            if acf.check_membership(fiveTuple):
                if fiveTuple not in st:
                    FP += 1
            else:
                if fiveTuple not in st:
                    TN += 1
    fp_rate = FP / (FP + TN)
    with res_map_lock:
        res_map[ratio] = fp_rate
    print("[Thread {}] ratio={} finished".format(tid, ratio))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ACF data structure on CAIDA traces")
    parser.add_argument('input_trace', type=str, help="input CAIDA trace file")
    parser.add_argument('sample', type=bool, help="use sample of the all traces")

    args = parser.parse_args()

    fiveTuple_list = load_trace(args.input_trace, args.sample)
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


    
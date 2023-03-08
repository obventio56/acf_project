"""
Run ACF data structure on CAIDA traces
"""

import argparse
import pickle
import threading
import matplotlib.pyplot as plt
from tqdm import tqdm

from acf_firewall import ACF


def add_bool_arg(parser, name, default=False):
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

def run_thread(tid, fiveTuple_list, ratio, n_flows, ACF_c, res_map, res_map_lock):
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
    acf = ACF(b=int(S_flows / 0.95), c=ACF_c)
    st = set()
    A_st = set()
    for fiveTuple in tqdm(fiveTuple_list, desc="[Thread {}]".format(tid)):
        # TODO: It seems hash_with_offset requires input to be integer
        # So we convert the fiveTuple back
        fiveTuple = int.from_bytes(fiveTuple, byteorder="little")
        if len(st) <= S_flows:
            if fiveTuple not in st:
                acf.insert(fiveTuple)
                st.add(fiveTuple)
        else:
            # The remaining are used to 
            # check false positive rate 
            if acf.check_membership(fiveTuple):
                if fiveTuple not in st:
                    FP += 1
                    # Now adaptive
                    acf.adapt_false_positive(fiveTuple)
            else:
                if fiveTuple not in st:
                    TN += 1
    fp_rate = FP / (FP + TN)
    with res_map_lock:
        res_map[ratio] = fp_rate
    print("[Thread {}] ratio={} finished".format(tid, ratio))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ACF data structure on CAIDA traces")
    parser.add_argument('-input_trace', type=str, help="input CAIDA trace file")
    add_bool_arg(parser, "sample")
    parser.add_argument('-sample_rate', type=float, default=0.1, help="the sample rate")
    args = parser.parse_args()

    fiveTuple_list = load_trace(args.input_trace, args.sample, args.sample_rate)
    n_flows, n_pkts = get_trace_stats(fiveTuple_list)


    ratio_list = [i for i in range(1, 6)] + [i * 10 for i in range(1, 11)]

    fig, ax = plt.subplots()
    C_list = [1, 4]
    marker_style_list = ["o", "v"]
    for marker_style, ACF_c in zip(marker_style_list, C_list):
        res_map_lock = threading.Lock()
        res_map = dict()
        # Parallel between each ratio
        thread_list = [threading.Thread(target=run_thread, 
                       args=(tid, fiveTuple_list, ratio, n_flows, ACF_c, res_map, res_map_lock)) \
                       for tid, ratio in enumerate(ratio_list)]
        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()

        fp_list = []
        for ratio in ratio_list:
            fp_list.append(res_map[ratio])
        ax.plot(ratio_list, fp_list, "-{}".format(marker_style), fillstyle="none", label="ACF (c={})".format(ACF_c))

    ax.set_xlabel("A/S ratio")
    ax.set_ylabel("False positive rate")
    ax.set_yscale('log')
    ax.legend()
    fig.savefig("res.png")


    
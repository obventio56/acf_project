"""
Run ACF data structure on CAIDA traces
"""

import argparse
import pickle

def load_trace(fname):
    with open(fname, "rb") as f:
        fiveTuple_list = pickle.load(f)
        return fiveTuple_list
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ACF data structure on CAIDA traces")
    parser.add_argument('input_trace', type=str, help="input CAIDA trace file")
    args = parser.parse_args()

    fiveTuple_list = load_trace(args.input_trace)

    if fiveTuple_list != None:
        print(len(fiveTuple_list))
    else:
        print("Trace file doesn't exist")

    
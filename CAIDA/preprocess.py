"""
Dump CAIDA trace to per-packet numpy array
"""
import argparse
import socket
import pickle

from scapy.all import *
from scapy.layers.all import IP, TCP, UDP
from tqdm import tqdm

def load_trace(input_pcap):
    fiveTuple_list = []
    for pkt in tqdm(PcapReader(input_pcap)):
        if IP in pkt and (TCP in pkt or UDP in pkt):
            sIP = pkt[IP].src
            dIP = pkt[IP].dst
            proto = pkt[IP].proto
            dport = pkt[TCP].dport if TCP in pkt else pkt[UDP].dport
            sport = pkt[TCP].sport if TCP in pkt else pkt[UDP].sport
            fiveTuple = socket.inet_aton(sIP) + socket.inet_aton(dIP) + \
                        sport.to_bytes(2, byteorder="little") + \
                        dport.to_bytes(2, byteorder="little") + \
                        proto.to_bytes(1, byteorder="little")
            fiveTuple_list.append(fiveTuple)
        else:
            continue
    return fiveTuple_list


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dump CAIDA pcap to numpy array")
    parser.add_argument('input_pcap', type=str, help="input CAIDA pcap file" )
    parser.add_argument('output_name', type=str, help="Output file name for dumped trace and stats")
    args = parser.parse_args()

    fiveTuple_list = load_trace(input_pcap=args.input_pcap)
    with open(args.output_name, "wb") as f:
        pickle.dump(fiveTuple_list, f)

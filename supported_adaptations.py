import struct
import math
import random
import crcmod
import numpy as np


def randomSrc():
    components = []
    for _ in range(6):
        components.append(f'{random.randint(0, 256):0x}')
    return ":".join(components)


def crc_from_eth(src):
    hash2_func = crcmod.predefined.mkCrcFun('crc-32-bzip2')
    src_hex = int(src[6:17].replace(":", ""), 16)
    return hash2_func(struct.pack("!I", src_hex)) & 0xffff


class CuckooFilter():
    def __init__(self, d, b, c):
        self.c = c
        self.bexp = b
        self.b = pow(2, b)
        self.d = d
        self.tables = np.full((d, self.b, self.c), None, dtype=object).tolist()
        self.backup = np.full((d, self.b, self.c), None, dtype=object).tolist()

    """
    def block_hash(self, fingerprint, i):
        fingerprintBytes = '{0:b}'.format(fingerprint).rjust(32, "0")
        return int(fingerprintBytes[(i + 1)*-(self.bexp):len(fingerprintBytes) - ((self.bexp)*(i))], 2)
    """

    def block_hash(self, fingerprint, i):
        hash2_func = crcmod.predefined.mkCrcFun('crc-32-bzip2')
        return hash2_func(struct.pack("!I", fingerprint + i)) % self.b

    def insert(self, x, badStates=[][:], depth=0):
        if depth > 935:
            return False

        fingerprint = crc_from_eth(x)

        # Insert into free space if possible, ignore bad states
        for j in range(0, self.d):

            if j in badStates:
                continue

            h = self.block_hash(fingerprint, j)
            for i in range(0, self.c):
                if self.tables[j][h][i] != None:
                    continue
                self.tables[j][h][i] = fingerprint
                self.backup[j][h][i] = [x, badStates.copy()]
                return True

        """
        For next week:
            TODO: make something smarter like optimizing the graph. Implement BFS

        Later:
        TODO: try other designs
        TODO: P4 implementation
            TODO: Optimize for data plane insertion
    
        Before march:
            - Design/benchmarking complete
        April: 
            - Implementation complete
            - Write up

        MVP: Benchmarking plus prototype
        """

        # Pick random item to cuckoo, excluding bad states
        h = None
        for i in range(0, self.d):
            if i in badStates:
                continue
            h = i
            break
        if h is None:
            return False

        # Rn picks 1 of 1, that's silly
        c = random.randint(0, self.c - 1)

        h_remove = self.block_hash(fingerprint, h)

        # Replace removed element with x
        new_insert = self.backup[h][h_remove][c]
        self.backup[h][h_remove][c] = [x, badStates.copy()]
        self.tables[h][h_remove][c] = fingerprint

        # Cuckoo x, tracking bad states
        return self.insert(new_insert[0], new_insert[1].copy(), depth=depth + 1)

    """ Search tables for fingerprint and return indices """

    def membership_index(self, x):
        fingerprint = crc_from_eth(x)
        for i in range(0, self.d):
            b = self.block_hash(fingerprint, i)
            for j in range(0, self.c):
                if self.tables[i][b][j] == fingerprint:
                    return (i, b, j)
        return False

    """ Returns true/false if x in ACF """

    def check_membership(self, x):
        membership_index = self.membership_index(x)
        if membership_index == False:
            return False
        return True

    """ Swaps collision of false_x with different item in same block """

    def adapt_false_positive(self, false_x):

        membershipIndex = self.membership_index(false_x)

        if membershipIndex == False:
            raise "False positive not in ACF"

        (h, b, c) = membershipIndex

        [x, xBadStates] = self.backup[h][b][c]
        xBadStates.append(h)

        x_fingerprint = crc_from_eth(x)

        # This is no longer random
        swap_index = None
        for i in range(0, self.d):
            if i in xBadStates:
                continue
            swap_index = i
            break
        if swap_index is None:
            return False

        # print(xBadStates, swap_index)

        b_index = self.block_hash(x_fingerprint, swap_index)

        # y here is value + bad states
        y = self.backup[swap_index][b_index][c]

        self.backup[swap_index][b_index][c] = [x, xBadStates.copy()]
        self.tables[swap_index][b_index][c] = x_fingerprint
        self.backup[h][b][c] = None
        self.tables[h][b][c] = None

        if y is not None:
            return self.insert(y[0], y[1].copy())

        return True

    def printState(self):
        print(self.tables)
        print(self.backup)

    def occupancy_stats(self):
        per_table = []
        for i in range(0, self.d):
            total = 0
            full = 0
            for j in range(0, self.b):
                for k in range(0, self.c):
                    total += 1
                    if self.tables[i][j][k] is not None:
                        full += 1
            per_table.append((total, full))
        print(per_table)

    """Currently assumes one cell per bucket"""

    def getDelta(self, regState):
        delta = []
        for i in range(0, self.d):
            for j in range(0, self.b):
                tableVal = self.tables[i][j][0]
                if tableVal is None:
                    tableVal = 0

                if not tableVal == regState[i][j]:
                    delta.append((i, j, tableVal // 4))
        return delta


configurations = [(2, 7, 1), (3, 7, 1), (4, 7, 1),
                  (5, 7, 1), (3, 8, 1), (3, 9, 1), (3, 10, 1)]


for configuration in configurations:
    print("Configuration: ", configuration)

    for occupancyRate in range(10, 99):
        achievedFalsePositives = []
        capacity = configuration[0]*pow(2, configuration[1])*configuration[2]
        occupancy = occupancyRate * capacity*0.01

        for _ in range(0, 5):

            testCuckoo = CuckooFilter(
                configuration[0], configuration[1], configuration[2])
            src_lst = []

            achievedCapacity = True

            for _ in range(0, math.floor(occupancy)):
                x = randomSrc()
                src_lst.append(x)
                if not testCuckoo.insert(x):
                    achievedCapacity = False
                    break

            if not achievedCapacity:
                continue

            falsePositives = 0
            while True:
                x = src_lst[falsePositives % len(src_lst)]

                if not testCuckoo.adapt_false_positive(x):
                    break
                falsePositives += 1

            achievedFalsePositives.append(falsePositives)

        if len(achievedFalsePositives) < 4:
            break

        print(capacity, math.floor(occupancy), len(achievedFalsePositives), np.mean(achievedFalsePositives),
              np.std(achievedFalsePositives))

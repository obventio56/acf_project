import struct
import math
import random
import crcmod
import numpy as np

"""
Generate a random MAC address.
"""


def randomSrc():
    components = []
    for _ in range(6):
        components.append(f'{random.randint(0, 256):0x}')
    return ":".join(components)


""" 
Compute the fingerprint for a given MAC address
"""


def crc_from_eth(src):
    hash2_func = crcmod.predefined.mkCrcFun('crc-32-bzip2')
    src_hex = int(src[6:17].replace(":", ""), 16)
    return hash2_func(struct.pack("!I", src_hex)) & 0xffff


"""
Compute sliding hash fingerprint from big hash at index i.
"""


def get_fingerprint_at_index(x, i, fingerprintLength=8):

    assert i + fingerprintLength <= 32

    fingerprint = crc_from_eth(x)
    fingerprintBytes = '{0:b}'.format(fingerprint).rjust(32, "0")
    return int(fingerprintBytes[i:(i + fingerprintLength)], 2)


class CuckooFilter():
    def __init__(self, d, b, c):
        self.c = c
        self.bexp = b
        self.b = pow(2, b)
        self.d = 1
        self.tables = np.full((d, self.b, self.c), None, dtype=object).tolist()
        self.backup = np.full((d, self.b, self.c), None, dtype=object).tolist()

    """
    Compute the bucket index for a given fingerprint and table index
    """

    def block_hash(self, fingerprint, i):
        hash2_func = crcmod.predefined.mkCrcFun('crc-32-bzip2')
        return hash2_func(struct.pack("!I", fingerprint + i)) % self.b

    """
    Calculate block hash and insert if space in bucket
    """

    def insert(self, x):

        h = self.block_hash(crc_from_eth(x), 0)
        for i in range(0, self.c):
            if self.tables[0][h][i] is None:
                self.tables[0][h][i] = [0, get_fingerprint_at_index(x, 0)]
                self.backup[0][h][i] = x
                return True

        return False

    """ Search tables for fingerprint and return indices """

    def membership_index(self, x):
        fingerprint = crc_from_eth(x)
        for i in range(0, self.d):
            b = self.block_hash(fingerprint, i)
            for j in range(0, self.c):

                if self.tables[i][b][j] is None:
                    continue

                if self.tables[i][b][j][1] == get_fingerprint_at_index(x, self.tables[i][b][j][0]):
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

        x = self.backup[h][b][c]
        [bad_hash_index, _] = self.tables[h][b][c]
        new_hash_index = bad_hash_index + 1

        if new_hash_index + 8 > 32:
            return False

        self.tables[h][b][c] = [new_hash_index,
                                get_fingerprint_at_index(x, new_hash_index)]

        return True

    """
    Print current state of the filter tables.
    """

    def printState(self):
        print(self.tables)
        print(self.backup)

    """
    Count items in filter. Useful as sanity check.
    """

    def countOccupancy(self):
        count = 0
        for i in range(0, self.d):
            for j in range(0, self.b):
                for k in range(0, self.c):
                    if self.tables[i][j][k] is not None:
                        count += 1
        print("Occupancy is: " + str(count))

    """
    Print the occupancy of each stage in the filter
    """

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

    """
    Get delta between CuckooFilter and tofino register state. Used to update tofino registers.
    """

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


configurations = [(1, 7, 8)]

# For each configuration
for configuration in configurations:
    print("Configuration: ", configuration)

    # For occupancy between 10% and 99%
    for occupancyRate in range(10, 99):
        achievedFalsePositives = []
        capacity = configuration[0]*pow(2, configuration[1])*configuration[2]
        occupancy = occupancyRate * capacity*0.01

        print(occupancy, capacity)

        # Run test up to five times
        for _ in range(0, 5):

            # Create new filter
            testCuckoo = CuckooFilter(
                configuration[0], configuration[1], configuration[2])

            # Track items we insert into the filter
            src_lst = []

            # Insert items until we reach the desired occupancy
            achievedCapacity = True
            for _ in range(0, math.floor(occupancy)):
                x = randomSrc()
                src_lst.append(x)
                if not testCuckoo.insert(x):
                    achievedCapacity = False
                    break

            if not achievedCapacity:
                continue

            # Simulate and count supported false positive adaptations
            falsePositives = 0
            while True:
                x = src_lst[falsePositives % len(src_lst)]

                adapted = True

                while True:
                    if not testCuckoo.adapt_false_positive(x):
                        adapted = False
                        break

                    # Simulate adaptation where 1/2 of the time it still collides with the same item (since we adjust only one bit)
                    if random.randint(0, 1) == 0:
                        break

                if not adapted:
                    break

                falsePositives += 1

            achievedFalsePositives.append(falsePositives)

        # If we didn't reach the desired occupancy for more than 1/5 of the runs, complete the configuration
        if len(achievedFalsePositives) < 4:
            break

        print(capacity, math.floor(occupancy), len(achievedFalsePositives), np.mean(achievedFalsePositives),
              np.std(achievedFalsePositives))

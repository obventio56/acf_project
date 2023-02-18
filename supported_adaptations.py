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


class CuckooFilter():
    def __init__(self, d, b, c):
        self.c = c
        self.bexp = b
        self.b = pow(2, b)
        self.d = d
        self.tables = np.full((d, self.b, self.c), None, dtype=object).tolist()
        self.backup = np.full((d, self.b, self.c), None, dtype=object).tolist()

    """
    Compute the bucket index for a given fingerprint and table index
    """

    def block_hash(self, fingerprint, i):
        hash2_func = crcmod.predefined.mkCrcFun('crc-32-bzip2')
        return hash2_func(struct.pack("!I", fingerprint + i)) % self.b

    """
    Find an insertion path for x by running BFS. An insertion path represents all the entries that need to 
    move in order to insert x.
    Takes x, the item to insert, and badStates, a list of tables that already have false-positives.
    Returns a list of table indices that represent the path to insert x.
    """

    def find_insertion_path(self, x, badStates=[][:]):
        searchQueue = [[[x, badStates], []]]
        for _ in range(0, 1000):
            if len(searchQueue) < 1:
                print("1000 iterations")
                break

            [[n, nbadStates], path] = searchQueue.pop(0)
            fingerprint = crc_from_eth(n)
            for i in range(0, self.d):
                if i in nbadStates:
                    continue

                # Calculate new path if we inserted into this table
                h = self.block_hash(fingerprint, i)
                newPath = path.copy()
                newPath.append(i)

                # If we found a free space, return the path so we can insert
                if self.tables[i][h][0] is None:
                    return newPath

                # Otherwise, push to the queue so we can check the next degree
                [newX, newBadStates] = self.backup[i][h][0]
                searchQueue.append([[newX, newBadStates], newPath])

        # No path found
        return False

    """
    Calculate insertion path and execute insertion operations
    """

    def insert(self, x, badStates=[][:]):

        insertionPath = self.find_insertion_path(x, badStates.copy())

        if insertionPath is False:
            return False

        # Setup initial insertion
        toInsert = [x, badStates.copy()]

        for i in range(0, len(insertionPath)):
            legTable = insertionPath[i]
            toInsertFingerprint = crc_from_eth(toInsert[0])
            h = self.block_hash(toInsertFingerprint, legTable)

            toInsertTmp = None
            if self.tables[legTable][h][0] is not None:
                toInsertTmp = self.backup[legTable][h][0].copy()

            self.tables[legTable][h][0] = toInsertFingerprint
            self.backup[legTable][h][0] = toInsert.copy()

            toInsert = toInsertTmp

        return True

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

        # Mark current position as bad
        xBadStates.append(h)

        # Remove from current position
        self.backup[h][b][c] = None
        self.tables[h][b][c] = None

        # Reinsert to try to find new position
        return self.insert(x, xBadStates.copy())

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


configurations = [(2, 7, 1), (3, 7, 1), (4, 7, 1),
                  (5, 7, 1), (3, 8, 1), (3, 9, 1), (3, 10, 1)]


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

                if not testCuckoo.adapt_false_positive(x):
                    break
                falsePositives += 1

            achievedFalsePositives.append(falsePositives)

        # If we didn't reach the desired occupancy for more than 1/5 of the runs, complete the configuration
        if len(achievedFalsePositives) < 4:
            break

        print(capacity, math.floor(occupancy), len(achievedFalsePositives), np.mean(achievedFalsePositives),
              np.std(achievedFalsePositives))

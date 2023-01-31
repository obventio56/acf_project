import hashlib
import random
import numpy as np

random.seed(10)

""" Compute sha256 of input plus offset.
Assuming sha256 is totally random and uniform, adding
small offset (i.e. index of table, or index of slot in block)
should provide a functionally unique hash function
"""
def hash_with_offset(x, n):
    return hashlib.sha256(str(x + n).encode()).hexdigest()

""" Return hash as integer, representing index into table.
Uses first 16 bits of hash """
def block_hash(x, n, b):
    return int(hash_with_offset(x,n)[0:4], 16) % b

""" Return 16 bit hex string, representing fingerprint of element """
def fingerprint_hash(x, n):
    return hash_with_offset(x, n + 2)[0:4]

""" An implimentation of an adjustable cuckoo filter 
using the cyclical adjustment mechanism using swapping adjustment
"""
class ACF:

    def __init__(self, b, c):
        self.c = c
        self.b = b
        self.h = 2
        self.tables = np.full((2, self.b, self.c), None, dtype=object).tolist()     # Table tracking fingerprints
        self.backup = np.full((2, self.b, self.c), None, dtype=object).tolist()     # Table tracking true values

    """ Insert x into the ACF 
    Returns False if element was successfully inserted and no element was kicked out.
    Returns x, representing element that was kicked out if max-depth was achieved and no
    free slot was found (e.g. the table is very full).
    """
    def insert(self, x, depth = 0):

        if depth > 10:
            return x

        for j in range(0,2):
            h = block_hash(x, j, self.b)
            for i in range(0, self.c):
                if self.tables[j][h][i] != None:
                    continue
                self.tables[j][h][i] = fingerprint_hash(x, i)
                self.backup[j][h][i] = x
                return False
        
        # Pick random element in block to cuckoo
        h = random.randint(0, 1)
        c = random.randint(0, self.c - 1)
        h_remove = block_hash(x, h, self.b)

        # Replace removed element with x
        new_insert = self.backup[h][h_remove][c]
        self.backup[h][h_remove][c] = x
        self.tables[h][h_remove][c] = fingerprint_hash(x, c)

        # Cuckoo x
        return self.insert(new_insert, depth=depth + 1)

    """ Search tables for fingerprint and return indices """
    def membership_index(self, x):
        for i in range(0,2):
            b = block_hash(x, i, self.b)
            for j in range(0, self.c):
                f = fingerprint_hash(x, j)
                if self.tables[i][b][j] == f:
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
        (h, b, c) = self.membership_index(false_x)
        
        swap_index = False
        for i in range(0, self.c):
            if self.tables[h][b][i] == None:
                swap_index = i
                break

        if swap_index == False:
            swap_index = random.randint(0, self.c - 1)
            if swap_index == c:
                swap_index = (swap_index + 1) % self.c


        x = self.backup[h][b][c]
        y = self.backup[h][b][swap_index]

        self.tables[h][b][c] = fingerprint_hash(y, c)
        self.tables[h][b][swap_index] = fingerprint_hash(x, swap_index)
        self.backup[h][b][c] = y
        self.backup[h][b][swap_index] = x

    def occupancy_stats(self):
        per_table = []
        for i in range(0, self.d):
            total = 0
            full = 0
            for j in range(0, self.b):
                for k in range(0, self.c):
                    total +=1
                    if self.tables[i][j][k] is not None:
                        full += 1
        print(per_table)


""" Rudimentary test routine for ACF:
1. Picks a random int, n
2. If n is true positive, asserts ACF agrees
3. If n is false positive, calls ACF adjust and asserts false positive is fixed
4. If n is true negative, inserts n and checks that it was inserted
"""
acf = ACF(100,4)
insert_list = []
while True:   
    print(len(insert_list)) 
    n = random.randint(0, 900000000)
    if n in insert_list:
        assert acf.check_membership(n)
    else:
        if acf.check_membership(n):
            acf.adapt_false_positive(n)
            assert not acf.check_membership(n)
        else:
            res = acf.insert(n)
            insert_list.append(n)
            if res:
                insert_list.remove(res)
            # Sometimes (rarely) the element that gets cuckooed out (due to depth limit)
            # is the element we were trying to insert originally. If this is the case, we
            # don't expect n to be in the acf
            if res == n: continue
            assert acf.check_membership(n)
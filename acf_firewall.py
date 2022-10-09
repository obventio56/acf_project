import hashlib
import random
import numpy as np

random.seed(10)

def hash_with_offset(x, n):
    return hashlib.sha256(str(x + n).encode()).hexdigest()

def block_hash(x, n, b):
    return int(hash_with_offset(x,n)[0:4], 16) % b

# Return the first 16 bits of hash as fingerprint
def fingerprint_hash(x, n):
    return hash_with_offset(x, n + 2)[0:4]

class ACF:

    def __init__(self, b, c):
        self.c = c
        self.b = b
        self.h = 2
        self.tables = np.full((2, self.b, self.c), None, dtype=object).tolist()
        self.backup = np.full((2, self.b, self.c), None, dtype=object).tolist()

    def insert(self, x, depth = 0):

        if depth > 10:
            return x

        h1 = block_hash(x, 0, self.b)
        h2 = block_hash(x, 1, self.b)

        #print(self.tables[0][h1], self.tables[1][h2])

        for i in range(0, self.c):
            if self.tables[0][h1][i] != None:
                continue
            self.tables[0][h1][i] = fingerprint_hash(x, i)
            self.backup[0][h1][i] = x
            return False
        
        for i in range(0, self.c):
            if self.tables[1][h2][i] != None:
                continue
            self.tables[1][h2][i] = fingerprint_hash(x, i)
            self.backup[1][h2][i] = x
            return False

        h = random.randint(0, 1)
        c = random.randint(0, self.c - 1)
        h_remove = h1
        if h == 1:
            h_remove = h2

        new_insert = self.backup[h][h_remove][c]
        self.backup[h][h_remove][c] = x
        self.tables[h][h_remove][c] = fingerprint_hash(x, c)

        # Cuckoo
        return self.insert(new_insert, depth=depth + 1)

    def membership_index(self, x):
        for i in range(0,2):
            b = block_hash(x, i, self.b)
            for j in range(0, self.c):
                f = fingerprint_hash(x, j)
                if self.tables[i][b][j] == f:
                    return (i, b, j)
        return False

    def check_membership(self, x):
        membership_index = self.membership_index(x)
        if membership_index == False:
            return False
        return True

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

acf = ACF(100,4)

insert_list = []
false_pos_count = 0

while True:    
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
            if res == n: continue
            assert acf.check_membership(n) and not (res == n)        

    
    
import matplotlib.pyplot as plt
from tqdm import tqdm
import json
import statistics as st
from util import *
from supported_adaptations import ACF
from matplotlib.ticker import FormatStrFormatter

X = []
Y = []
Err = []

for i in range(2, 17):
    f = open('param_results/stages{}.json'.format(i))

    # returns JSON object as
    # a dictionary
    payload = json.load(f)
    X.append(payload[0])
    Y.append(payload[1])
    Err.append(st.pstdev(payload[2]))
    f.close()


print(X, Y, Err)
print(len(X), len(Y), len(Err))


fig, ax = plt.subplots()
ax.plot(X, Y)
ax.errorbar(X, Y, yerr=Err, fmt='o')

ax.set_title("Optimal # Stages")
ax.set_xlabel("# Stages")
ax.set_ylabel("Maximum Occupancy")
ax.yaxis.set_major_formatter(FormatStrFormatter('%d %%'))
ax.grid(True)
ax.legend()
fig.savefig("formatted/optimal.png")

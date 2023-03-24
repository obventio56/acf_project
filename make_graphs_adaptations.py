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

for i in range(1, 9):
    f = open('param_results/capacity{}.json'.format(i))

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

ax.set_title("# Supported Adaptations at each Occupancy")
ax.set_xlabel("Occupancy %")
ax.set_ylabel("# Supported Adaptations")
ax.xaxis.set_major_formatter(FormatStrFormatter('%d %%'))
ax.grid(True)
ax.legend()
fig.savefig("formatted/adaptations.png")

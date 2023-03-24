import matplotlib.pyplot as plt
from tqdm import tqdm


from util import *
from supported_adaptations import ACF



C_list = [True, False]
label_list = ["ACF", "CF"]
marker_style_list = ["o", "v"]

data = [
    [[[1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100], [0.004203694826505402, 0.004883388060958154, 0.0035091769594828583, 0.004102674256256041, 0.003929312672537127, 0.0033022953659592896, 0.003455265825117479, 0.003452056418158113, 0.00359063817415322, 0.003738660571944527, 0.0033777263076626134, 0.0036505298716865992, 0.0030421969007619074, 0.0036251487934206256, 0.0031071003998703124]], [
        [1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100], [0.02765588701648291, 0.021834919031180712, 0.02876601639155027, 0.021028890559553218, 0.02945976988332964, 0.029468023675472788, 0.08513774993089468, 0.08113073367310655, 0.0683529582788196, 0.02938728291079415, 0.10222792069925828, 0.040292042389734925, 0.027814371664108866, 0.06061302889297695, 0.027058791743218416]]],
    [
        [[1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100], [0.0044763058696822835, 0.0032850927816745093, 0.003006935350889956, 0.004528733500262759, 0.003387366431634804, 0.0030129251959034346,
                                                                    0.002781694902157745, 0.0021903679263592757, 0.0020699310309287206, 0.002136973630702251, 0.0018880146617372895, 0.002118301353401992, 0.001740183677537065, 0.0019028405052843944, 0.0019106922643606413]],
        [[1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100], [0.0400511577813678, 0.033827577022107785, 0.03053817676253294, 0.03820829082815543, 0.025078142036781274, 0.019356145481245174,
                                                                    0.2276160488341994, 0.04132124472047393, 0.13336024529971055, 0.10207238599484894, 0.12403229374032294, 0.011839378837014043, 0.014849056314490287, 0.010622282338736178, 0.024930347274028288]]

    ]

]

totalList = []
for trace in data:
    for series in trace:
        totalList += series[1]
yMin = min(totalList)
yMax = max(totalList)

for j, trace in enumerate(data):

    fig, ax = plt.subplots()
    for i, series in enumerate(trace):
        ax.plot(series[0], series[1], "-{}".format(marker_style_list[i % 2]),
                fillstyle="none", label=label_list[i % 2])

    ax.set_title("Trace {}".format(j))
    ax.set_xlabel("A/S ratio")
    ax.set_ylabel("False positive rate")
    ax.set_yscale('log')
    ax.set_ylim((yMin*0.95, yMax*1.05))
    ax.grid(True)
    ax.legend()
    fig.savefig("formatted/res_{}_{}.png".format(0xff, j))

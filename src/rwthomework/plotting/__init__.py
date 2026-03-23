from numpy import array, abs, argmin
from matplotlib.pyplot import gca, subplots_adjust


class Convert:
    cm_to_mm = 1e1
    keV_to_MeV = 1e-3
    inch_to_cm = 2.54


convert = Convert()

PLOT_WIDTH = 14
PLOT_SIZE = array([
    PLOT_WIDTH / convert.inch_to_cm,
    11/20 * PLOT_WIDTH / convert.inch_to_cm
])
PLOT_SIZE_S = array([
    PLOT_WIDTH / 2 / convert.inch_to_cm,
    PLOT_WIDTH / 2 * 5/6 / convert.inch_to_cm
])
PLOT_SIZE2 = array([
    PLOT_WIDTH / convert.inch_to_cm,
    13/20 * PLOT_WIDTH / convert.inch_to_cm
])

ERRORBAR_FORMAT = {"fmt": ".", "elinewidth": .7, "capsize": 1.7, "zorder": -1}
SUBPLOTS_ADJUST = {"left": .15, "right": .85, "bottom": .2, "top": .95}


def textrm(*args):
    if len(args) == 2:
        s = r'$\displaystyle\frac{\textrm{' + args[0]
        s += r'}}{\textrm{' + args[1]
        s += r'}}$'
    else:
        s = r'$\textrm{' + args[0] + r'}$'
    return s


def replace_nearestxtick(val):
    ax = gca()
    ticks = ax.get_xticks()
    ticks[argmin(abs(ticks - val))] = val
    ax.set_xticks(ticks)


def center_plot(left_margin=0.15, top_margin=.95):
    subplots_adjust(left=left_margin, right=1-left_margin, bottom=.2, top=top_margin)

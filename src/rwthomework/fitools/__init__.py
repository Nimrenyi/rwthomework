from matplotlib import lines as mpl_lines, patches as mpl_patches

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
from odrpack import odr_fit

from ..plotting import PLOT_SIZE2


class Multi_Gauss():
    def __init__(self, num_peaks, noise=None):
        self.num_peaks = num_peaks

        self.expected_args = 1 + 3*self.num_peaks

        if noise == 'linear':
            self.expected_args += 2

        self.noise = noise

    def gauss_peak(self, x, mean, sigma, amplitude):
        return amplitude * np.exp(- (x - mean)**2 / (2*sigma**2))

    def linear_noise(self, x, slope, pos):
        return slope * (x - pos)

    def __call__(self, *args):
        f"""Evaluate {self.num_peaks} gaussian peaks at a value or range of values

        Raises:
            Exception: checks whether enough parameters where given

        Returns:
            float: evaluated value
        """

        if not len(args) == self.expected_args:
            raise Exception(f'Not the right number of arguments, got {len(args)}, expected {self.expected_args}. \n')

        x = args[0]
        f = 0
        for i in range(self.num_peaks):
            f += self.gauss_peak(x, *args[3*i+1:3*i+4])

        if self.noise == 'linear':
            f += self.linear_noise(x, *args[-2:])

        return f


def curve_fit_lsq(f, x, y, p0, ey=[], bounds=(-np.inf, np.inf), verbose=False, fit_window=[]):
    """Curve fit wrapper

    Args:
        f (function): optimize target
        x (array_like): x-data
        y (array_like): y-data
        p0 (array_like, optional): starting parameters. Defaults to None1.
        yerror (array_like, optional): errors on y-data. Defaults to None.

    Returns:
        list: popt, perr, chi2, dof, cov
    """
    if not any(ey):
        ey = np.ones(len(y))

    if len(fit_window):
        x = x[fit_window]
        y = y[fit_window]
        ey = ey[fit_window]

    dof = len(y) - len(p0)

    popt, cov = curve_fit(
        f,
        x,
        y,
        p0,
        ey,
        absolute_sigma=1,
        bounds=bounds
    )

    perr = np.sqrt(np.diag(cov))

    chi2 = (np.square((f(x, *popt) - y) / ey)).sum()

    if verbose:
        print(f'chi2/dof = {chi2:.1g}/{dof} = {chi2/dof:.2g}')
        print('1σ-int:', chi2_sigma_intervall(dof))

    return popt, perr, chi2, dof, cov


def chi2_sigma_intervall(dof):
    return 1 + np.array([-1, 1]) * np.sqrt(2/dof)


def linear_reg_odr(x, y, ex, ey, p0, fit_window=[]):
    """lin reg ODR

    Args:
        x (_type_): _description_
        y (_type_): _description_
        ex (_type_): _description_
        ey (_type_): _description_
        p0 (_type_): _description_

    Returns:
        list: popt, perr, chi2, dof, cov
    """
    if len(fit_window):
        x = x[fit_window]
        y = y[fit_window]
        ex = ex[fit_window]
        ey = ey[fit_window]

    def f(x, beta):
        return beta[0]*x + beta[1]

    sol = odr_fit(f, x, y, p0)

    popt = sol.beta
    perr = sol.sd_beta

    chi2 = np.sum((sol.eps / np.sqrt(ey**2 + (popt[0]*ex)**2))**2)

    dof = len(x)-2
    cov = sol.cov_beta

    return popt, perr, chi2, dof, cov


class Data:
    errbar_kwargs = {"fmt": ".", "elinewidth": 0.7, "capsize": 2, "zorder": 60}
    scatter_kwargs = {"marker": ".", "zorder": 60}

    def __init__(self, x, y, err, label=None, color=None, errscale=1):
        self.x = np.array(x)
        self.y = np.array(y)
        if err is not None:
            self.err = err * np.ones_like(self.x)
        else:
            self.err = np.zeros_like(self.x)
        self.errscale = errscale

        if not label:
            self.label = fr"$\textrm{{Data}} \pm {errscale}\sigma$"
        else:
            self.label = label

        if color is not None:
            self.errbar_kwargs["color"] = color
            self.scatter_kwargs["color"] = color

        self.artists = []

    def plot(self, axs):
        err_not_zero = (self.err != 0)

        eb = axs[0].errorbar(x=self.x[err_not_zero], y=self.y[err_not_zero], yerr=self.err[err_not_zero]*self.errscale, **self.errbar_kwargs)

        if "color" not in self.scatter_kwargs:
            self.scatter_kwargs["color"] = eb[0].get_color()

        sc = axs[0].scatter(self.x[1-err_not_zero], self.y[1-err_not_zero], **self.scatter_kwargs)

        self.artists += [eb, sc]

    def getLegendHandle(self):
        return self.artists[0]


class Fit:
    fit_kwargs = {"lw": 2, "zorder": 70}
    err_kwargs = {"alpha": 0.5, "zorder": 40}
    pull_kwargs = {"fmt": ".", "elinewidth": 0.7, "capsize": 3, "zorder": 20}

    def __init__(self, f, points: list, params: list, err=None, label=None, fit_color=None, pull_color=None, errscale=1, err_args=()):
        self.err_args = err_args

        self.params = params
        self.fit_function = f
        self.has_err = (err is not None)
        self._err = err
        self.errscale = errscale
        self.limits = [np.min(points), np.max(points)]

        self.points = points

        if label:
            self.label = label
        else:
            self.label = r"$\textrm{Fit}$"

            if self.has_err:
                self.label += fr' $\pm {errscale}\sigma$'

        if fit_color is not None:
            self.fit_kwargs["color"] = fit_color
            self.err_kwargs["color"] = fit_color

        if pull_color is not None:
            self.pull_kwargs["color"] = pull_color

        self.artists = []

    def fit(self, x):
        return self.fit_function(x, *self.params)

    def err(self, x):
        return self._err(x, *self.params, *self.err_args)

    def plot(self, axs, data):
        # plot line
        fit_yy = self.fit(self.points)
        ln = axs[0].plot(self.points, fit_yy, **self.fit_kwargs)
        self.artists += [ln]

        # plot band
        if self.has_err:
            kwargs = {"color": ln[0].get_color()}
            kwargs.update(self.err_kwargs)
            err = self.err(self.points)
            fb = axs[0].fill_between(self.points, fit_yy - err*self.errscale, fit_yy + err*self.errscale, **kwargs)
            self.artists += [fb]

        # plot pulls
        section = (self.limits[0] <= data.x) & (data.x <= self.limits[1])
        x_values = data.x[section]
        data_y = data.y[section]
        data_err = data.err[section]
        fit_y = self.fit(x_values)

        errors = data_err**2

        if self.has_err:
            errors += self.err(x_values)**2

        errors = np.sqrt(errors)
        pulls = np.where(errors != 0, (data_y-fit_y)/errors, data_y-fit_y)

        kwargs = {"color": ln[0].get_color()}
        kwargs.update(self.pull_kwargs)
        kwargs["zorder"] = 50
        eb = axs[1].errorbar(x=x_values, y=pulls, yerr=1, **kwargs)
        self.artists += [eb]

        self.pulls = pulls

    def getLegendHandle(self):
        ln = mpl_lines.Line2D([], [], c=self.artists[0][0].get_color())
        if self.has_err:
            ar = mpl_patches.Patch(fc=self.artists[1].get_facecolor(), alpha=0.5)
            return (ln, ar)

        return ln


def plot(data: Data, fit: Fit | list[Fit], labels: list[str] = [], pull_statistic: bool = True, pull_statistic_color: str = "gray", add_to_legend=[[], []]):
    while len(labels) < 2:
        labels += [None]

    if len(labels) < 3:
        labels += [r"$\textrm{pulls}$"]

    fig, axs = plt.subplots(
        2, 1,
        figsize=PLOT_SIZE2,
        sharex=True,
        gridspec_kw={'height_ratios': [5, 2]}
    )

    if labels[0] is not None:
        axs[1].set_xlabel(labels[0])
    if labels[1] is not None:
        axs[0].set_ylabel(labels[1])
    if labels[2] is not None:
        axs[1].set_ylabel(labels[2])

    legend_handles = []
    legend_labels = []
    artists = []
    pulls = []

    data.plot(axs)
    artists += [data.artists]
    if data.label is not None:
        legend_handles += [data.getLegendHandle()]
        legend_labels += [data.label]

    if isinstance(fit, list) and len(fit) == 1:
        fit = fit[0]

    if isinstance(fit, list):
        for fi in fit:
            fi.plot(axs, data)
            artists += [fi.artists]
            pulls += fi.pulls.tolist()
            if fi.label is not None:
                legend_handles += [fi.getLegendHandle()]
                legend_labels += [fi.label]
    else:
        if ("color" not in fit.pull_kwargs):
            fit.pull_kwargs["color"] = data.artists[0][0].get_color()
        fit.plot(axs, data)
        artists += [fit.artists]
        pulls += fit.pulls.tolist()
        if fit.label is not None:
            legend_handles += [fit.getLegendHandle()]
            legend_labels += [fit.label]

    pulls = np.array(pulls)
    if pull_statistic_color is not None:
        xlim = axs[0].set_xlim()
        artists += [plot_pull_statistic(axs, pulls, xlim, pull_statistic_color)]
        axs[0].set_xlim(xlim)

    fig.tight_layout()
    fig.subplots_adjust(hspace=0)

    axs[0].legend(handles=legend_handles + add_to_legend[0], labels=legend_labels + add_to_legend[1])

    return fig, axs, artists, pulls


def plot_pull_statistic(axs, pulls, xlim, color):
    mu = pulls.mean()
    sigma = pulls.std(ddof=1)

    ln = axs[1].axhline(mu, xlim[0], xlim[1], color=color, zorder=-1, lw=1)
    fb = axs[1].fill_between(xlim, mu-sigma, mu+sigma, color=color, alpha=0.5, zorder=-1)

    ylim = axs[1].set_ylim()
    ylim = np.max(np.abs(ylim)) * np.array([-1, 1])
    axs[1].set_ylim(ylim)

    return [ln, fb]


def main():
    peaks = Multi_Gauss(2, 'linear')
    print(peaks(
        0,
        *[-1, 1, 2],
        *[1, 1, 2],
        1, 1
    ))

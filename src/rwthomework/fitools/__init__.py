from matplotlib import lines as mpl_lines, patches as mpl_patches

import matplotlib.pyplot as plt
import numpy as np
import inspect
import warnings
from scipy.optimize import curve_fit
from odrpack import odr_fit
from uncertainties.unumpy import uarray

from ..textools import write_data_table
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


def meta_curve_fit(
    func, x, y,
    p0=[], ex=[], ey=[],
    x_window=[],
    fit_specifier='',
    add_to_dict=dict(),
    parameter_table_from_names=[],
    verbose=False,
    table_kwargs=dict(),
    **kwargs
):
    fit_needs_odr = bool(len(ex))

    def vprint(msg):
        if verbose:
            print(msg)

    # create function for curve_fit or odr_fir
    if fit_needs_odr:
        def f(x, beta):
            return func(x, *beta)

    else:
        def f(x, *args):
            # print(args)
            return func(x, *args)

    # Check y-errors
    if isinstance(ey, (float, int)):
        ey = np.ones_like(y) * ey

    if not any(ey):
        vprint('You did not provide any errors on the y-data. Using np.ones instead.')
        ey = np.ones_like(x)

    # Check x-errors
    if isinstance(ex, (float, int)):
        ex = np.ones_like(x) * ex

    if not any(ex):
        ex = np.ones_like(x) * min(ey) * 1e-100

    # Check and apply window
    if any(x_window):
        x_window = list(sorted(x_window))
        if len(x_window) == 2:
            vprint('Got interval boundaries. Determining fit_window...')
            x_window = (x > np.array(x_window[0])) & (x < np.array(x_window[1]))

        x = np.array(x)[x_window]
        y = np.array(y)[x_window]
        ey = np.array(ey)[x_window]
        ex = np.array(ex)[x_window]

    parameter_number = len(inspect.signature(func).parameters) - 1
    if not len(p0):
        p0 = np.ones(parameter_number)

    dof = len(y) - parameter_number

    if fit_needs_odr:
        result = odr_fit(f, x, y, p0, weight_x=1/ex**2, weight_y=1/ey**2, **kwargs)

        popt = result.beta
        cov = result.cov_beta
        perr = result.sd_beta
        chi2 = result.sum_square

    else:
        popt, cov = curve_fit(f, x, y, p0, ey, absolute_sigma=1, **kwargs)
        perr = np.sqrt(np.diag(cov))
        chi2 = (np.square((f(x, *popt) - y) / ey)).sum()

    upopt = uarray(popt, perr)

    vprint(f'chi2/dof = {chi2:.3e}/{dof} = {chi2/dof:.3e}')
    vprint(f'1-sigma-interval: {chi2_sigma_intervall(dof)}')

    add_to_dict[fit_specifier] = {
        'popt': upopt,
        'cov': cov,
        'chi2': chi2,
        'dof': dof,
        'chi2/dof': chi2/dof,
        'chi2-interval': chi2_sigma_intervall(dof)
    }

    if any(parameter_table_from_names):
        parameter_names = parameter_table_from_names

        if len(parameter_names) != parameter_number:
            vprint(f'Your parameter names ({len(parameter_names)}) do not match the number of arguments ({parameter_number}).')
            parameter_names = [f'$p_{i}$' for i in range(parameter_number)]

        write_data_table(
            parameter_names, upopt,
            name=fit_specifier,
            header=['parameter', 'value'],
            table=False,
            **table_kwargs
        )

    return popt, perr, chi2, dof, cov


def curve_fit_lsq(f, x, y, p0=[], ey=[], bounds=(-np.inf, np.inf), verbose=False, fit_window=[], add_to_dict=('', dict()), **kwargs):
    """scipy curve_fit wrapper with chi2 statistics, fit_window and dictionary updater

    Args:
        f (callable): fit function
        x (ArrayLike): X-data
        y (ArrayLike): Y-data
        p0 (ArrayLike): Inital guess for parameters. Defauls to 1 for all parameters
        ey (ArrayLike, optional): Y-erors. Defaults to 1.
        bounds (tuple, optional): Bounds for parameters, see curve_fit. Defaults to (-np.inf, np.inf).
        verbose (bool, optional): Print everything. Defaults to False.
        fit_window (list, optional): Either a boolean array for indexing, or tuple of (xmin, xmax) for fitting. Defaults to [].
        add_to_dict (tuple, optional): Dict-key and dict in which resus and staistics will be added. Defaults to ('', dict()).

    Returns:
        list: popt, perr, chi2, dof, cov
    """
    warnings.warn("'curve_fit_lsq' is deprecated since rwthomework 0.0.4.0 you should use 'meta_curve_fit' instead!", DeprecationWarning, stacklevel=2)

    return meta_curve_fit(f, x, y, p0=p0, ey=ey, x_window=fit_window, bounds=bounds, verbose=verbose, fit_specifier=add_to_dict[0], add_to_dict=add_to_dict[1], **kwargs)


def chi2_sigma_intervall(dof):
    return 1 + np.array([-1, 1]) * np.sqrt(2/dof)


def linear_reg_odr(x, y, ex, ey, p0, fit_window=[], **kwargs):
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
    def f(x, beta):
        return beta[0]*x + beta[1]

    warnings.warn("'linear_reg_odr' is deprecated since rwthomework 0.0.4.0 you should use 'meta_curve_fit' instead!", DeprecationWarning, stacklevel=2)

    return meta_curve_fit(f, x, y, p0, ex, ey, fit_window, **kwargs)


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
    x = np.arange(20)
    y = np.arange(20) + np.random.randn(20)

    fit_window = [1, 18]

    ex = np.ones_like(x)
    ey = np.ones_like(y)

    def f(x, a, b):
        return a*x + b

    dicti = {'a': 1}

    curve_fit_lsq(f, x, y, ey=ey)
    print(dicti)

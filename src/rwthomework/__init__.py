from matplotlib.pyplot import savefig, rcParams
from numpy import zeros, sqrt
from glob import glob
import inspect
import shutil
import time
import sys
import os


class Exercise:
    """
    Generic CMdP Exercise Class with helpful functions and automatic function name printing.

    Provides the functions:
        - recursive_filesearch
        - setup_plots_dir
        - setup_plots_dir
        - save_plot
        - print_fit_results
        - print_optimize_results

    Methods that run automatically:
        - tracefunc
        - clear_old_plots
    """
    def __init__(self, version='', verbose=True, plot_dark_mode=False):
        self.version = version
        self.verbose = verbose
        self.plot_dark_mode = plot_dark_mode
        self.start_time = time.time()

        importing_filename = inspect.stack()[1].filename
        filepath = os.path.dirname(importing_filename)
        os.chdir(filepath)
        if filepath.endswith('scripts'):
            os.chdir('..')
        self.plots_dir = self.setup_plots_dir()

        self.exercise_number = sys.argv[0][-5:-3]
        self.EXERCISE_NAME = 'Aufgabenteil'

    def check_version(self):
        from importlib.metadata import version

        if version('rwthomework') != self.version:
            raise Exception(
                'Das Skript braucht version von rwthomework', self.version,
                '\n Diese kann z.B. mit pip install --force-reinstall rwthomework==', self.version
            )

    def recursive_filesearch(self, file_name):
        """
        Searches in the file-tree for files matching the name.

        Args:
            file_name (str): pattern that must be contained

        Returns:
            str: path of the first file that was found.
        """
        search_results = glob(f'**/*{file_name}*', recursive=True)
        if search_results:
            return search_results[0]
        return ''

    def setup_plots_dir(self):
        """
        Setups a plots/ folder

        Returns:
            str: path of the plots folder
        """
        rcParams.update({
            'text.usetex': True,
            'font.family': 'sans-serif',
            'font.sans-serif': ['CMU Sans Serif', 'Helvetica'],
            'savefig.format': 'pdf',
            'font.size': 16.0,
            'font.weight': 'bold',
            'axes.labelsize': 'medium',
            'axes.labelweight': 'bold',
            'axes.linewidth': 1.2,
            'lines.linewidth': 2.0,
        })

        if self.plot_dark_mode:
            rcParams.update({
                "ytick.color": "w",
                "xtick.color": "w",
                "axes.labelcolor": "w",
                "axes.edgecolor": "w",
                'legend.facecolor': '0.15',
                'legend.edgecolor': 'w',
                'legend.labelcolor': 'w'
            })

        if not os.path.exists('plots'):
            os.mkdir('plots')
        return 'plots/'

    def clear_old_plots(self):
        """
        Deletes old plots from the exercise.
        Only looks at plots that start with the exercise name.
        """
        directory = self.plots_dir

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if not os.path.isfile(file_path):
                return
            file_mtime = os.path.getmtime(file_path)
            if file_mtime > self.start_time:
                return
            is_from_exercise = sys.argv[0][-5:-3] == filename[:2]
            if is_from_exercise:
                os.remove(file_path)

    def save_plot(self, name: str):
        """
        Saves a plot in the plot-directory.
        The exercise number is appended automatically

        Args:
            name (str): name for the plot
        """
        plot_name = f'{self.plots_dir}{self.exercise_number}-{name}'
        savefig(plot_name, transparent=self.plot_dark_mode)

    def print_fit_results(self, par, cov):
        """
        Print parameters and errors

        Args:
            par (numpy.ndarray): array of fitted parameters by leastsquare
            cov (numpy.ndarray): array of covariances
        """
        def GetKorrelationMatrix(cov):
            rho = zeros(cov.shape)
            for i in range(cov.shape[0]):
                for j in range(cov.shape[0]):
                    rho[i, j] = cov[i, j]/(sqrt(cov[i, i])*sqrt(cov[j, j]))

            return rho
        rho = GetKorrelationMatrix(cov)
        print("\n      Fit parameters                correlationen")
        print("-------------------------------------------------------")
        for i in range(len(par)):
            Output = f"{i:3.0f} par = {par[i]:.3e} +/- {sqrt(cov[i, i]):.3e}"
            for j in range(len(par)):
                Output += f"   {rho[i, j]:.2f} "

            print(Output, '\n')

    def print_optimize_results(self, res):
        stat_dict = {
            1: 'yes',
            0: 'no'
        }
        s = (f"The algorithm finished sucessfully: {stat_dict[res.success]}\n"
             f"The optimal parameters are {res.x}\n"
             f"The minimal function value is {res.fun}")
        print(s, '\n')

    def run(self):
        for method in self.__dir__():
            if not method[:-1].endswith('exercise_'):
                continue
            if self.verbose:
                print(f'\nAufgabenteil ({method[-1]})\n')
            getattr(self, method)()
        self.clear_old_plots()


def main():
    from importlib.metadata import version

    test = Exercise(version('rwthomework'))
    test.setup_plots_dir()
    test.save_plot('s')
    shutil.rmtree('plots/')


if __name__ == "__main__":
    main()

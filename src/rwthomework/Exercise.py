from matplotlib.pyplot import savefig, rcParams
from numpy import zeros, sqrt
from glob import glob
import inspect
import shutil
import time
import sys
import os
import re


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
    def __init__(self, version, verbose=True):
        self.version = version
        importing_filename = inspect.stack()[1].filename
        filepath = os.path.dirname(importing_filename)
        os.chdir(filepath)
        if filepath.endswith('scripts'):
            os.chdir('..')
        self.start_time = time.time()
        self.plots_dir = self.setup_plots_dir()

        if verbose:
            sys.setprofile(self.tracefunc)

        self.exercise_number = sys.argv[0][-5:-3]
        self.EXERCISE_NAME = 'Aufgabenteil'

    def check_version(self):
        from importlib.metadata import version

        if version('rwthomework') != self.version:
            raise Exception('Das Skript braucht version von rwthomework', self.version)

    def tracefunc(self, frame, event, arg):
        """
        Trace function to monitor the execution of specific functions.

        This method is designed to be used as a tracing function for Python's
        built-in `sys.settrace()` functionality. It tracks function calls and
        returns to provide insights into the execution flow of certain functions
        within the class.

        Parameters:
            frame (frame): The current stack frame.
            event (str): A string indicating the type of event that occurred.
                        Can be either "call" or "return".
            arg (any): Additional argument relevant to the event type. Typically,
                    this is not used in this implementation.

        Behavior:
            - On a "call" event: If the called function's name matches the pattern
            'exercise_[a-z]', it extracts the last character after 'exercise_'
            and prints a message indicating which exercise is being executed.

            - On a "return" event: If the returned function's name is 'save_plot',
            it invokes `self.clear_old_plots()` to clean up old plot data.

        Returns:
            function: Returns itself (`self.tracefunc`) to continue tracing.
        """
        function_name = frame.f_code.co_name
        if event == "call":
            if re.search(r'exercise_[a-z]', function_name):
                s = re.search(r'exercise_[a-z]', function_name).group()[-1]
                print(f'\n{self.EXERCISE_NAME} ({s})')

        if event == "return":
            if re.search(r'save_plot', function_name):
                self.clear_old_plots()
        return self.tracefunc

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
        print('removed old plots')

    def save_plot(self, name: str):
        """
        Saves a plot in the plot-directory.
        The exercise number is appended automatically

        Args:
            name (str): name for the plot
        """
        savefig(f'{self.plots_dir}{self.exercise_number}-{name}')

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


def main():
    test = Exercise()
    test.setup_plots_dir()
    test.save_plot('s')
    shutil.rmtree('plots/')


if __name__ == "__main__":
    main()

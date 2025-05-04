import sys
import numpy as np
import matplotlib.pyplot as plt
import glob
import time
import os
import re


class Exercise:
    """Generic Exercise Class with helpful functions and automatic function name printing.
    THE CONTENTS OF THIS CLASS ARE NOT CONTRIBUTING TO THE SOLUTION OF THE EXERCISES!
    """
    def __init__(self, verbose=True):
        self.start_time = time.time()
        self.plots_dir = self.setup_plots_dir()
        self.clear_old_plots()

        self.print_patterns = {
            r'exercise_[a-z]': lambda s: f'\n{self.EXERCISE_NAME} ({s})'
        }

        if verbose:
            sys.setprofile(self.tracefunc)

        self.EXERCISE_NAME = 'Aufgabenteil'

    def tracefunc(self, frame, event, arg):
        if event != "call":
            return self.tracefunc
        function_name = frame.f_code.co_name
        for re_pattern, message in self.print_patterns.items():
            if re.search(re_pattern, function_name):
                s = re.search(r'exercise_[a-z]', function_name).group()[-1]
                print(message(s))
        return self.tracefunc

    def recursive_filesearch(file_name):
        search_results = glob(f'**/*{file_name}', recursive=True)
        if search_results:
            return search_results[0]
        return ''

    def setup_plots_dir(self):
        filepath = os.path.dirname(__file__)
        os.chdir(filepath)
        if filepath.endswith('scripts'):
            os.chdir('..')

        plt.rcParams.update({
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
        directory = self.plots_dir

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_mtime = os.path.getmtime(file_path)
                if file_mtime + 60 < self.start_time:
                    os.remove(file_path)

    def save_plot(self, name: str):
        plt.savefig(self.plots_dir + name)

    def print_fit_results(par, cov):
        """Print parameters and errors

        Args:
            par (numpy.ndarray): array of fitted parameters by leastsquare
            cov (numpy.ndarray): array of covariances
        """
        def GetKorrelationMatrix(cov):
            rho = np.zeros(cov.shape)
            for i in range(cov.shape[0]):
                for j in range(cov.shape[0]):
                    rho[i, j] = cov[i, j]/(np.sqrt(cov[i, i])*np.sqrt(cov[j, j]))

            return rho
        rho = GetKorrelationMatrix(cov)
        print("\n      Fit parameters                correlationen")
        print("-------------------------------------------------------")
        for i in range(len(par)):
            Output = f"{i:3.0f} par = {par[i]:.3e} +/- {np.sqrt(cov[i, i]):.3e}"
            for j in range(len(par)):
                Output += f"   {rho[i, j]:.2f} "

            print(Output, '\n')


class A1(Exercise):
    def __init__(self, verbose=True):
        super().__init__(verbose)

    def exercise_a(self):
        print('foo')

    def exercise_b(self):
        print('bar')

    def exercise_c(self):
        print('blub')

    def exercise_d(self):
        print('blub')

    def run(self):
        self.exercise_a()
        self.exercise_b()
        self.exercise_c()
        self.exercise_d()


def main():
    a1 = A1()
    a1.run()


if __name__ == "__main__":
    main()

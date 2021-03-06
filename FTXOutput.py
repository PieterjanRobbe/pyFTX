# import statements
import matplotlib.pyplot as plt
import numpy as np
import os
import shutil

# special imports
from pyFTX.FTXSimulation import FTXSimulation
from pyFTX.utils import save, load

class FTXOutput():

    def __init__(self, ftx_simulation:FTXSimulation):
        self.ftx_simulation = ftx_simulation
        self.retention = None
        self.surface = None

    def load_surface(self):
        surface_files = [os.path.join(run.get_work_dir(), "work", "workers__xolotlWorker_3", "surface.txt") for run in self.ftx_simulation.get_runs()]
        surfaces = [np.loadtxt(surface_file).reshape(-1, 2) for surface_file in surface_files if os.path.isfile(surface_file) and os.path.getsize(surface_file)]
        allSurface_files = [os.path.join(run.get_work_dir(), "work", "workers__xolotlWorker_3", "allSurface.txt") for run in self.ftx_simulation.get_runs()]
        allSurfaces = [np.loadtxt(allSurface_file) for allSurface_file in allSurface_files if os.path.isfile(allSurface_file) and os.path.getsize(allSurface_file)]
        surface = np.unique(np.vstack(surfaces + allSurfaces), axis=0)
        surface[:, 1] = surface[0, 1] - surface[:, 1] # subtract baseline
        self.surface = (surface[:, 0], surface[:, 1])

    def load_retention(self):
        retentionOut_files = [os.path.join(run.get_work_dir(), "work", "workers__xolotlWorker_3", "retentionOut.txt") for run in self.ftx_simulation.get_runs()]
        retentionOuts = [np.loadtxt(retentionOut_file) for retentionOut_file in retentionOut_files if os.path.isfile(retentionOut_file) and os.path.getsize(retentionOut_file)]
        allRetentionOut_files = [os.path.join(run.get_work_dir(), "work", "workers__xolotlWorker_3", "allRetentionOut.txt") for run in self.ftx_simulation.get_runs()]
        allRetentionOuts = [np.loadtxt(allRetentionOut_file) for allRetentionOut_file in allRetentionOut_files if os.path.isfile(allRetentionOut_file) and os.path.getsize(allRetentionOut_file)]
        # retention = np.vstack([np.vstack([x, y]) for x, y in zip(allRetentionOuts, retentionOuts)])
        retention = np.unique(np.vstack(retentionOuts + allRetentionOuts), axis=0)
        self.retention = (retention[1:, 0], 100*(retention[1:, 5] + retention[1:, 2]) / (retention[1:, 1] * self.get_sticking_coeff())) # 100*(He content + He bulk ) / (He fluence * He sticking coeff)

    def get_surface(self):
        """Get surface growth data to plot"""
        if self.surface is None:
            print("No surface data found, execute 'load_surface()' first")
            raise ValueError("FTXPy -> FTXOutput -> get_surface() : No surface data found, execute 'load_surface()' first")
        return self.surface

    def get_retention(self):
        """Get He retention data to plot"""
        if self.retention is None:
            print("No retention data found, execute 'load_retention()' first")
            raise ValueError("FTXPy -> FTXOutput -> get_retention() : No retention data found, execute 'load_retention()' first")
        return self.retention

    def get_sticking_coeff(self):
        runs = self.ftx_simulation.get_runs()
        tridyn_dat_file = os.path.join(runs[-1].get_work_dir(), "work", "workers__xolotlWorker_3", "tridyn.dat")
        if os.path.isfile(tridyn_dat_file):
            with open(tridyn_dat_file, "r") as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith("He"):
                        return float(line.split()[-1])
        else:
            print(f"File {tridyn_dat_file} does not exist!")
            raise ValueError("FTXPy -> FTXOutput -> get_sticking_coeff() : File does not exist")

    def plot_surface(self, t_end=None, figsize=(8, 5), kwargs={"linewidth": .75}, ax=None)->None:
        """Plot surface growth"""
        t, x = self.get_surface()
        if not t_end is None:
            t = np.append(t, t_end)
            x = np.append(x, x[-1])
        if ax is None:
            _, ax = plt.subplots(figsize=figsize)
            ax.set_xlabel("time [s]")
            ax.set_ylabel("surface growth [nm]")
        ax.step(t, x, where="post", **kwargs)
        return ax

    def plot_retention(self, figsize=(8, 5), kwargs={"linewidth": .75}, ax=None)->None:
        """Plot He retention"""
        t, x = self.get_retention()
        if ax is None:
            _, ax = plt.subplots(figsize=figsize)
            ax.set_xlabel("time [s]")
            ax.set_ylabel("He retention [%]")
        ax.plot(t, x, **kwargs)
        return ax

    def save(self, overwrite:bool=False)->None:
        """Save this FTX output"""
        file_name =  os.path.join(self.ftx_simulation._path, "output.pk")
        if overwrite and os.path.isfile(file_name):
            os.remove(file_name)
        if os.path.isfile(file_name):
            print(f"File {file_name} already exists, use 'overwrite=True' to overwrite the output file")
            raise ValueError("FTXPy -> FTXOutput -> save() : File already exists, use 'overwrite=True' to overwrite the output file")
        save(self, file_name)

    def load(file_name:str):
        """Load an FTX output from file"""
        if not os.path.isfile(file_name):
            print(f"File {file_name} does not exist")
            raise ValueError("FTXPy -> FTXOutput -> load() : File does not exist")
        return load(file_name)
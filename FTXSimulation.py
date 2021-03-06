# import statements
from codecs import ignore_errors
import h5py
import os
import shutil
import sys

# special imports
from pyFTX.FTXRun import FTXRun
from pyFTX.utils import save, load, get_last_occurance

# add path to keepLastTS.py
sys.path.append("/project/projectdirs/atom/users/" + os.environ.get("USER") + "/ips-wrappers/ips-iterative-xolotlFT/python_scripts_for_coupling")
import keepLastTS

# class that represents an FTX simulation
class FTXSimulation():
    """
    A class to represent an FTX simulation

    Methods
    -------
    get_runs()
        Returns a list of FTX runs that compose this simulation
    start()
        Start this FTX simulation
    restart()
        Restart this FTX simulation
    is_running()
        Check if this FTX simulation is currently running
    is_queueing()
        Check if this FTX simulation is currently queueing
    has_started()
        Check if this FTX simulation has started
    has_finished()
        Check if this FTX simulation has finished
    has_exceeded_the_time_limit()
        Check if this FTX simulation has been killed because it exceeded the specified time limit
    has_failed()
        Check if this FTX simulation has failed because of another error
    save()
        Save this FTX simulation
    load()
        Load an FTX simulation from file
    status()
        Returns the status of this simulation
    print_status()
        Prints the status of this simulation
    step()
        Execute the next step in this simulation
    """

    def __init__(self, current_run:FTXRun):
        """
        Constructs all the necessary attributes for the FTXSimulation object

        Parameters
        ----------
            current_run : FTXRun
                The FTX run to use as a basis for this FTX simulation
        """
        self.current_run = current_run
        self._runs = list()
        self._path = self.current_run.get_work_dir()
        self._name = os.path.split(self._path)[-1]
        self._basename = self._name

    def get_runs(self):
        """Returns a list of FTX runs that compose this simulation"""
        return self._runs

    def start(self)->None:
        """Start this FTX simulation"""
        self._name = "init_" + self._basename
        self.current_run.change_work_dir(os.path.join(self._path, self._name))
        self.current_run.write_files()
        self._start_current_run()

    def _start_current_run(self):
        self.current_run.start()
        self._runs.append(self.current_run)

    def restart(self)->None:
        """Restart this FTX simulation"""
        src = self.current_run.get_work_dir()
        self._name = "restart_" + self._basename + f"_{len(self._runs)}"
        dest = os.path.join(self._path, self._name)
        shutil.copytree(src, dest)
        self.current_run = FTXRun(dest, self.current_run.inputs, self.current_run.batchscript)
        self._prepare_restart()
        self.current_run.write_files(overwrite=True)
        self.current_run.clean()
        self._start_current_run()

    def _prepare_restart(self)->None:
        self._keep_last_ts()
        self._copy_last_tridyn()
        self._update_restart_parameters()

    def _keep_last_ts(self)->None:
        work_dir = self.current_run.work_dir
        src = os.path.join(work_dir, "work", "workers__xolotlWorker_3", "xolotlStop.h5")
        dest = os.path.join(work_dir, "networkFile.h5")
        if os.path.isfile(dest):
            os.remove(dest)
        keepLastTS.keepLastTS(inFile=src, outFile=dest)

    def _copy_last_tridyn(self)->None:
        work_dir = self.current_run.work_dir
        src = os.path.join(work_dir, "work", "workers__ftridynWorker_2", "last_TRIDYN.dat")
        dest = os.path.join(work_dir, "last_TRIDYN.dat")
        shutil.copyfile(src, dest)

    def _update_restart_parameters(self)->None:
        self.current_run.inputs.parameters["START_MODE"].set_value("RESTART")
        self.current_run.inputs.parameters["ts_atol"].set_value(1e-3)
        self.current_run.inputs.parameters["ts_rtol"].set_value(1e-3)
        parameters = self._get_restart_parameters_from_log_file()
        for key, val in parameters.items():
            self.current_run.inputs.parameters[key].set_value(val)

    def _get_restart_parameters_from_log_file(self):
        parameters = dict()
        log_ftx = self.current_run.get_log_file()
        line_nb = get_last_occurance(log_ftx, "check for updates in time steps")
        parameters["LOOP_N"] = int(log_ftx[line_nb].split()[2][:-1])
        if "no update" in log_ftx[line_nb + 1]:
            parameters["LOOP_TIME_STEP"] = float(log_ftx[line_nb + 1].split("(")[1].split(")")[0])
            parameters["start_stop"] = float(log_ftx[line_nb + 1].split("(")[2].split(")")[0])
        else:
            parameters["LOOP_TIME_STEP"] = float(log_ftx[line_nb + 3].split()[6])
            parameters["start_stop"] = float(log_ftx[line_nb + 3].split()[9][1:])
        line_nb = get_last_occurance(log_ftx, "change in Xolotls")
        parameters["ts_adapt_dt_max"] = float(log_ftx[line_nb + 1].split()[-1])
        line_nb = get_last_occurance(log_ftx, "driver time (in loop)")
        parameters["INIT_TIME"] = float(log_ftx[line_nb].split()[-1])
        parameters["XOLOTL_MAX_TS"] = self.current_run.inputs.parameters["XOLOTL_MAX_TS"].get_value() if parameters["INIT_TIME"] < 5 else 0.1
        line_nb = get_last_occurance(log_ftx, "updated the values of voidPortion")
        if line_nb > -1:
            parameters["voidPortion"] = float(log_ftx[line_nb].split()[-1])
            parameters["grid_size"] = float(log_ftx[line_nb].split()[-1])
        return parameters

    def has_started(self)->bool:
        """Check if this FTX simulation has started"""
        return self.current_run.has_started()

    def is_running(self)->bool:
        """Check if this FTX simulation is currently running"""
        return self.current_run.is_running()

    def is_queueing(self)->bool:
        """Check if this FTX simulation is currently queueing"""
        return self.current_run.is_queueing()

    def has_exceeded_the_time_limit(self)->bool:
        """Check if this FTX simulation has been killed because it exceeded the specified time limit"""
        return self.current_run.has_exceeded_the_time_limit()

    def has_finished(self)->bool:
        """Check if this FTX simulation has finished"""
        return self.current_run.has_finished()

    def has_failed(self)->bool:
        """Check if this FTX simulation has failed because of another error"""
        return self.current_run.has_failed()

    def save(self, overwrite:bool=False)->None:
        """Save this FTX simulation"""
        file_name =  os.path.join(self._path, "simulation.pk")
        if overwrite and os.path.isfile(file_name):
            os.remove(file_name)
        if os.path.isfile(file_name):
            print(f"File {file_name} already exists, use 'overwrite=True' to overwrite the simulation file")
            raise ValueError("FTXPy -> FTXSimulation -> save() : File already exists, use 'overwrite=True' to overwrite the simulation file")
        save(self, file_name)

    def load(file_name:str):
        """Load an FTX simulation from file"""
        if not os.path.isfile(file_name):
            print(f"File {file_name} does not exist")
            raise ValueError("FTXPy -> FTXSimulation -> load() : File does not exist")
        return load(file_name)

    def status(self)->None:
        """Returns the status of this FTX simulation"""
        if not self.has_started():
            status = "has not started"
        elif self.is_queueing():
            status = "is queueing"
        elif self.is_running():
            status = "is running"
        elif self.has_exceeded_the_time_limit():
            status = "has exceeded the time limit"
        elif self.has_finished():
            status = "has finished"
        elif self.has_failed():
            status = "has failed"
        else:
            status = "has unknown status"
        return self._get_print_name() + " " + status

    def _get_print_name(self):
        if self._name.startswith("init_"):
            return self._basename + " (init)"
        elif self._name.startswith("restart_"):
            return self._basename + " (restart " + self._name.split("_")[-1] + ")"
        return self._basename

    def print_status(self):
        """Prints the status of this FTX simulation"""
        print(self.status())

    def step(self):
        """Execute the next step in this simulation"""
        if not self.has_started():
            self.start()
        elif self.has_exceeded_the_time_limit():
            self.restart()
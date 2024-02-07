import logging
import os
import datetime

import reframe as rfm
import reframe.core.builtins as blt
import reframe.utility.sanity as sn

import numpy as np

import harness

logger = logging.getLogger(__name__)


SPECHPC_ROOT_LOOKUP = {
    "personal": "/home/lilith/Developer/SPEChpc/hpc2021-1.1.7",
    "csd3-power-scaling": "/rds/user/fb609/hpc-work/SPEChpc/hpc2021-1.1.7",
}


def _lookup_spechpc_root_dir(cluster_name: str) -> str:
    return SPECHPC_ROOT_LOOKUP[cluster_name]


def _benchmark_binary_name(benchmark_name: str) -> str:
    """
    Get the benchmark binary name from the benchmark specification. E.g.,
    "635.weather_s" becomes "weather".
    """
    return os.path.join(".", benchmark_name.split(".")[1].split("_")[0])


def _extract_perf_values(socket, key, fd, group):
    return sn.extractall(
        rf"(?P<time>\S+)\s+S{socket}\s+\d+\s+(?P<energy>\S+) \w+ {key}",
        fd,
        group,
        float,
    )


@rfm.simple_test
class SPEChpc(rfm.RegressionTest):

    valid_systems = ["*"]
    valid_prog_environs = ["*"]

    spechpc_benchmark = variable(str, value="635.weather_s")
    spechpc_dir = variable(str, type(None), value=None)

    time_series = variable(dict, value={})

    # todo: this depends on the system. can we add it to the environ?
    perf_events = [
        harness.PerfEvents.power.energy_cores,
        harness.PerfEvents.power.energy_pkg,
    ]

    build_system = harness.SPEChpcBuild()

    modules = ["rhel8/default-icl", "intel-oneapi-mkl/2022.1.0/intel/mngj3ad6"]

    spectimes_path = "spectimes.txt"
    executable = _benchmark_binary_name(spechpc_benchmark)
    executable_opts = ["output6.test.txt", "2400", "1000", "750", "625", "1", "1", "6"]

    num_nodes = 1

    # database specifics
    database_query_start_date = variable(datetime.datetime, type(None), value=None)
    database_query_end_date = variable(datetime.datetime, type(None), value=None)
    database_query_node_name = variable(str, type(None), value=None)

    @blt.run_before("compile")
    def set_build_variables(self):
        # learn things about the partition we're running on
        self.num_tasks = self.current_partition.processor.num_cpus
        self.partition_name = self.current_partition.name

        if not self.spechpc_dir:
            self.spechpc_dir = _lookup_spechpc_root_dir(self.current_system.name)

        # build system needs some additional info that reframe doesnt pass by
        # default
        self.build_system.spechpc_dir = self.spechpc_dir
        self.build_system.spechpc_num_ranks = self.num_tasks
        self.build_system.executable = self.executable
        self.build_system.stagedir = self.stagedir
        self.build_system.spechpc_benchmark = self.spechpc_benchmark

    @blt.run_before("run")
    def wrap_perf_events(self):
        # use the perf wrapper only if we're measuring perf events
        if self.perf_events:
            self.job.launcher = harness.PerfLauncherWrapper(
                self.job.launcher,
                self.perf_events,
                prefix=True,
            )

        if not self.executable_opts:
            # read the executable args from the build directory
            self.executable_opts = self.build_system.read_executable_opts()

        # for the database query, need a rough estimate of when to start query
        self.database_query_start_date = harness.get_query_time(start=True)

    @blt.run_after("run")
    def set_database_end_time(self):
        self.database_query_end_date = harness.get_query_time(start=False)

        # after the run we ask the job where it ran
        if self.job.nodelist:
            self.database_query_node_name = self.job.nodelist[0]
        else:
            logger.warn("No nodelists set by scheduler. Cannot query database")

    @blt.performance_function("J")
    def extract_perf_energy_event(self, key=None, socket=0):
        if not key:
            raise ValueError("`key` has no value")

        if socket < 0:
            raise ValueError("`socket` cannot be negative")

        # todo: this could easily be a single query instead of two
        # if we hand roll the regex capture instead
        all_time_measurements = _extract_perf_values(socket, key, self.stderr, "time")
        all_energy_measurements = _extract_perf_values(
            socket, key, self.stderr, "energy"
        )

        # save all measurements to the time series dictionary
        self.time_series[f"perf/{socket}/{key}"] = [
            all_time_measurements,
            all_energy_measurements,
        ]

        # return the summed energy
        return sum(all_energy_measurements)

    @blt.performance_function("J")
    def extract_database_readings(self):
        # get the pdu measurements
        values = harness.fetch_pdu_measurements(
            self.database_query_start_date,
            self.database_query_end_date,
            self.partition_name,
            self.database_query_node_name,
        )

        time_values = values[:, 0]
        power_values = values[:, 0]

        # todo: seemingly have to conver it to numpy array??
        self.time_series[f"BMC/{self.database_query_node_name}"] = [
            list(time_values),
            list(power_values),
        ]

        # integrate under the power curve to get the total energy
        return np.trapz(power_values, time_values)

    @blt.performance_function("s")
    def extract_core_time(self):
        return sn.extractsingle(r"Core time:\s+(\S+)", self.spectimes_path, 1, float)

    @blt.run_before("performance")
    def set_performance_variables(self):
        # build the selected perf events dictionary
        perf_events_gather = {
            f"{socket}/{k}": self.extract_perf_energy_event(k, socket)
            for k in self.perf_events
            for socket in range(self.current_partition.processor.num_sockets)
        }

        self.perf_variables = {
            **perf_events_gather,
            # add other measurements that are always available
            "Core time": self.extract_core_time(),
        }

        # if database is enabled, add that performance variable too
        if harness.DATABASE_QUERY_ENABLED:
            # board managment controller
            self.perf_variables[f"BMC/{self.database_query_node_name}"] = (
                self.extract_database_readings()
            )

    @blt.sanity_function
    def assert_passed(self):
        return sn.assert_found(r"Verification: PASSED", self.spectimes_path)

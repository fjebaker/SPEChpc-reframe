import logging

import reframe as rfm
import reframe.core.builtins as blt
import reframe.utility.sanity as sn

import numpy as np

import harness
import harness.utils as utils

logger = logging.getLogger(__name__)


@rfm.simple_test
class SPEChpc(rfm.RegressionTest):

    valid_systems = ["*"]
    valid_prog_environs = ["*"]

    spechpc_benchmark = variable(str, value="635.weather_s")
    spechpc_dir = variable(str, type(None), value=None)

    time_series = variable(dict, value={})

    # some job configurations
    exclusive_access = True
    # arbitrarily chosen to be long enough that scheduler doesn't kill it
    time_limit = "0d12h0m0s"

    # todo: this depends on the system. can we add it to the environ?
    perf_events = [
        harness.PerfEvents.power.energy_cores,
        harness.PerfEvents.power.energy_pkg,
    ]

    build_system = harness.SPEChpcBuild()

    modules = ["rhel8/default-icl", "intel-oneapi-mkl/2022.1.0/intel/mngj3ad6"]

    spectimes_path = "spectimes.txt"
    executable = utils.benchmark_binary_name(spechpc_benchmark)
    executable_opts = ["output6.test.txt", "2400", "1000", "750", "625", "1", "1", "6"]

    num_nodes = 1

    # database specifics
    job_start_time = variable(str, type(None), value=None)
    job_end_time = variable(str, type(None), value=None)
    database_query_node_name = variable(str, type(None), value=None)

    @blt.run_before("compile")
    def set_build_variables(self):
        # learn things about the partition we're running on
        self.num_tasks = self.current_partition.processor.num_cpus
        self.partition_name = self.current_partition.name

        if not self.spechpc_dir:
            self.spechpc_dir = utils.lookup_spechpc_root_dir(self.current_system.name)

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

        # get a rough start time estimate. may be refined later
        self.job_start_time = utils.time_now(True)

    @blt.run_after("run")
    def set_database_end_time(self):
        # for the database query, need a rough estimate of when to start query
        self.job_end_time = utils.time_now(False)

        # can we get a better estimate from the scheduler?
        maybe_better_times = utils.query_runtime(self.job)
        if maybe_better_times:
            self.job_start_time = maybe_better_times[0]
            self.job_end_time = maybe_better_times[1]

        # after the run we ask the job where it ran
        if self.job.nodelist:
            logger.debug("Nodelist for job %s: %s", self.job.jobid, self.job.nodelist)
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
        all_time_measurements = utils.extract_perf_values(
            socket, key, self.stderr, "time"
        )
        all_energy_measurements = utils.extract_perf_values(
            socket, key, self.stderr, "energy"
        )

        # save all measurements to the time series dictionary
        self.time_series[f"perf/{socket}/{key}"] = [
            # explicitly call list, as the `_extract_perf_values` returns
            # reframe deferrables
            list(all_time_measurements),
            list(all_energy_measurements),
        ]

        # return the summed energy
        return sum(all_energy_measurements)

    @blt.performance_function("J")
    def extract_database_readings(self):
        # get the pdu measurements
        values = harness.fetch_pdu_measurements(
            self.job_start_time,
            self.job_end_time,
            self.partition_name,
            self.database_query_node_name,
        )

        time_values = values[:, 0]
        power_values = values[:, 1]

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

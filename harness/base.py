import logging

import reframe as rfm
import reframe.core.builtins as blt
import reframe.utility.sanity as sn
import reframe.utility.typecheck as typ

import numpy as np

import harness
import harness.utils as utils

logger = logging.getLogger(__name__)


class SPEChpcBase(rfm.RunOnlyRegressionTest):

    valid_systems = ["*"]
    valid_prog_environs = ["*"]

    time_series = variable(dict, value={})

    cooldown_seconds = variable(int, value=60)

    # some job configurations
    exclusive_access = True
    # arbitrarily chosen to be long enough that scheduler doesn't kill it
    time_limit = "0d12h0m0s"

    modules = ["rhel8/default-icl", "intel-oneapi-mkl/2022.1.0/intel/mngj3ad6"]

    spectimes_path = "spectimes.txt"

    # database specifics
    job_start_time = variable(str, type(None), value=None)
    job_end_time = variable(str, type(None), value=None)
    database_query_node_names = variable(typ.List[str], type(None), value=None)

    @blt.run_before("run")
    def configure_pre_post_commands(self):
        # learn things about the partition we're running on
        self.num_tasks = self.spechpc_binary.num_runtime_ranks
        self.partition_name = self.current_partition.name

        self.executable = self.spechpc_binary.executable
        self.prerun_cmds = [
            # fetch the executable from the fixture
            f"cp {self.spechpc_binary.executable_path} {self.executable}",
        ]

        # copy over possible additional files
        self.prerun_cmds += [
            f"cp {self.spechpc_binary.relpath(f)} {f}"
            for f in self.spechpc_binary.additional_inputs
        ]

        self.postrun_cmds = [
            # after the run has finished and all measurements are made
            # rest the node for a bit before the next job sweeps in so
            # the database measurements are sane
            f'echo "Sleeping for {self.cooldown_seconds} seconds"',
            f"sleep {self.cooldown_seconds}s",
        ]

        if not self.executable_opts:
            # read the executable args from the build directory
            self.executable_opts = self.spechpc_binary.read_executable_opts()

        # get a rough start time estimate. may be refined later
        self.job_start_time = utils.time_now(True)

        # todo: there must be a better / more idiomatic way to do this
        # i would have thought reframe would have done this automatically
        self.job.options.append(f"--nodes={self.num_nodes}")

    @blt.run_after("run")
    def set_database_end_time(self):
        # for the database query, need a rough estimate of when to start query
        self.job_end_time = utils.time_now(False)

        # can we get a better estimate from the scheduler?
        maybe_better_times = utils.query_runtime(self.job)
        if maybe_better_times:
            self.job_start_time = maybe_better_times[0]
            self.job_end_time = maybe_better_times[1]

        # adjust the cooldown period in the recorded end time
        self.job_end_time = utils.subtract_cooldown(
            self.job_end_time, self.cooldown_seconds
        )

        # after the run we ask the job where it ran
        if self.job.nodelist:
            logger.debug("Nodelist for job %s: %s", self.job.jobid, self.job.nodelist)
            self.database_query_node_names = self.job.nodelist
        else:
            logger.warn("No nodelists set by scheduler. Cannot query database")

    @blt.performance_function("J")
    def extract_database_readings(self, nodename=None):
        if not nodename:
            raise ValueError("`nodename` must be defined")

        # get the pdu measurements
        values = harness.fetch_pdu_measurements(
            self.job_start_time,
            self.job_end_time,
            self.partition_name,
            nodename,
        )

        time_values = values[:, 0]
        power_values = values[:, 1]

        # todo: seemingly have to conver it to numpy array??
        self.time_series[f"BMC/{nodename}"] = [
            list(time_values),
            list(power_values),
        ]

        # integrate under the power curve to get the total energy
        return np.trapz(power_values, time_values)

    @blt.performance_function("s")
    def extract_spechpc_time(self, key="Core time"):
        return sn.extractsingle(rf"{key}:\s+(\S+)", self.spectimes_path, 1, float)

    @blt.run_before("performance")
    def set_performance_variables(self):
        self.perf_variables = {
            # add measurements that are always available
            "Core time": self.extract_spechpc_time("Core time"),
            "Total time": self.extract_spechpc_time("Total time"),
        }

        # if database is enabled, add that performance variable too
        if harness.DATABASE_QUERY_ENABLED:
            # board managment controller
            for nodename in self.database_query_node_names:
                self.perf_variables[f"BMC/{nodename}"] = self.extract_database_readings(
                    nodename
                )

    @blt.sanity_function
    def assert_passed(self):
        return sn.assert_found(r"Verification: PASSED", self.spectimes_path)

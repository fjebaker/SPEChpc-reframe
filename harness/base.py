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
    time_series = variable(dict, value={})

    valid_systems = ["*"]
    valid_prog_environs = ["*"]

    # some job configurations
    exclusive_access = True
    # arbitrarily chosen to be long enough that scheduler doesn't kill it
    time_limit = "0d12h0m0s"

    # modules required to run this test
    modules = ["rhel8/default-icl", "intel-oneapi-mkl/2022.1.0/intel/mngj3ad6"]

    # the output file path needed to test the sanity of the benchmark run
    spectimes_path = "spectimes.txt"

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

        if not self.executable_opts:
            # read the executable args from the build directory
            self.executable_opts = self.spechpc_binary.read_executable_opts()

        # get a rough start time estimate. may be refined later
        self.job_start_time = utils.time_now(True)

        # todo: there must be a better / more idiomatic way to do this
        # i would have thought reframe would have done this automatically
        self.job.options.append(f"--nodes={self.num_nodes}")

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

    @blt.sanity_function
    def assert_passed(self):
        return sn.assert_found(r"Verification: PASSED", self.spectimes_path)

import logging
import os

import reframe as rfm
import reframe.core.builtins as blt
import reframe.utility.sanity as sn

import harness

logger = logging.getLogger(__name__)


def _benchmark_binary_name(benchmark_name: str) -> str:
    """
    Get the benchmark binary name from the benchmark specification. E.g.,
    "635.weather_s" becomes "weather".
    """
    return os.path.join(".", benchmark_name.split(".")[1].split("_")[0])


@rfm.simple_test
class SPEChpc(rfm.RegressionTest):

    valid_systems = ["*"]
    valid_prog_environs = ["*"]

    spechpc_benchmark = variable(str, value="635.weather_s")

    # todo: this depends on the system. can we add it to the environ?
    perf_events = [
        harness.PerfEvents.power.energy_cores,
        harness.PerfEvents.power.energy_pkg,
    ]

    build_system = harness.SPEChpcBuild()

    modules = [
        "rhel8/default-icl",
        "intel-oneapi-mkl/2022.1.0/intel/mngj3ad6"
    ]

    # todo: can we do this better?
    build_system.spechpc_dir = "/home/lilith/Developer/SPEChpc/hpc2021-1.1.7"

    spectimes_path = "spectimes.txt"
    executable = _benchmark_binary_name(spechpc_benchmark)
    executable_opts = ["output6.test.txt", "2400", "1000", "750", "625", "1", "1", "6"]

    num_nodes = 1

    @blt.run_before("compile")
    def set_build_variables(self):
        self.num_tasks = self.current_partition.processor.num_cpus
        # build system needs some additional info that reframe doesnt pass by
        # default
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

    @blt.performance_function("J")
    def extract_perf_energy_event(self, key=None):
        if not key:
            raise ValueError("`key` has no value")
        return sn.extractsingle(
            rf"(\S+) \w+ {key}", self.stderr, 1, lambda x: float(x.replace(",", "_"))
        )

    @blt.performance_function("s")
    def extract_core_time(self):
        return sn.extractsingle(r"Core time:\s+(\S+)", self.spectimes_path, 1, float)

    @blt.run_before("performance")
    def set_performance_variables(self):
        # build the selected perf events dictionary
        perf_events_gather = {
            k: self.extract_perf_energy_event(k) for k in self.perf_events
        }

        # get the pdu measurements
        database_gather = harness.fetch_pdu_measurements("jobname", 1)

        self.perf_variables = {
            **perf_events_gather,
            **database_gather,
            # add other measurements that are always available
            "Core time": self.extract_core_time(),
        }

    @blt.sanity_function
    def assert_passed(self):
        return sn.assert_found(r"Verification: PASSED", self.spectimes_path)

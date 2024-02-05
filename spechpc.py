import os

import reframe as rfm
import reframe.core.builtins as blt
import reframe.core.launchers as lnr
import reframe.utility.sanity as sn
import reframe.utility.typecheck as typ

import harness


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

    build_system = harness.SPEChpcBuild()

    # todo: can we do this better?
    build_system.spechpc_dir = "/home/lilith/Developer/SPEChpc/hpc2021-1.1.7"
    # todo: this depends on the system. can we add it to the environ?
    perf_events = [
        harness.PerfEvents.power.energy_cores,
        harness.PerfEvents.power.energy_pkg,
    ]

    spectimes_path = variable(str, type(None), value="spectimes.txt")

    executable = _benchmark_binary_name(build_system.spechpc_benchmark)
    executable_opts = ["output6.test.txt", "2400", "1000", "750", "625", "1", "1", "6"]

    num_tasks = 12

    @blt.run_before("compile")
    def set_build_variables(self):
        self.build_system.executable = self.executable
        self.build_system.stagedir = self.stagedir

    @blt.run_before("run")
    def wrap_perf_events(self):

        # use the perf wrapper
        self.job.launcher = harness.PerfLauncherWrapper(
            self.job.launcher,
            self.perf_events,
            prefix=True,
        )

        if not self.executable_opts:
            # read the executable args from the build directory
            self.executable_opts = self.build_system.read_executable_opts()

    @blt.performance_function("s", perf_key="Core Time")
    def extract_core_time(self):
        return sn.extractsingle(r"Core time:\s+(\S+)", self.spectimes_path, 1, float)

    @blt.performance_function("J", perf_key="Energy cores")
    def extract_energy_cores(self):
        return sn.extractsingle(r"(\S+) \w+ power/energy-cores/", self.stderr, 1, float)

    @blt.performance_function("J", perf_key="Energy pkg")
    def extract_energy_pkg(self):
        return sn.extractsingle(r"(\S+) \w+ power/energy-pkg/", self.stderr, 1, float)

    @blt.sanity_function
    def assert_passed(self):
        return sn.assert_found(r"Verification: PASSED", self.spectimes_path)

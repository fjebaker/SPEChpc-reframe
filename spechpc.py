import os

import reframe as rfm
import reframe.core.builtins as blt
import reframe.utility.sanity as sn

from harness.build import SPEChpcBuild

def _benchmark_binary_name(benchmark_name: str) -> str:
    """
    Get the benchmark binary name from the benchmark specification. E.g.,
    "635.weather_s" becomes "weather".
    """
    return os.path.join(".", benchmark_name.split(".")[1].split("_")[0])

@rfm.simple_test
class HelloTest(rfm.RegressionTest):

    valid_systems = ["*"]
    valid_prog_environs = ["*"]

    build_system = SPEChpcBuild()
    # todo: can we do this better?
    build_system.spechpc_dir = "/home/lilith/Developer/SPEChpc/hpc2021-1.1.7"

    spectimes_path = variable(str, type(None), value="spectimes.txt")

    executable = _benchmark_binary_name(build_system.spechpc_benchmark)
    executable_opts = ["output6.test.txt", "2400", "1000", "750", "625", "1", "1", "6"]

    num_tasks = 12

    @blt.run_before("compile")
    def set_build_variables(self):
        self.build_system.executable = self.executable
        self.build_system.stagedir = self.stagedir

    @blt.sanity_function
    def assert_passed(self):
        return sn.assert_found(r"Verification: PASSED", self.spectimes_path)

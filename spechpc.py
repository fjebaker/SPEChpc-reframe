import logging

import reframe as rfm
import reframe.core.builtins as blt

import harness
import harness.config as config

F_MHZ = config.F_MHZ

logger = logging.getLogger(__name__)


class SetupPerfEvents(rfm.RegressionMixin):
    @blt.run_after("setup")
    def set_perf_events(self):
        partition_name = self.current_partition.name
        if partition_name in (config.SAPPHIRE, config.ICELAKE):
            self.perf_events = [
                harness.PerfEvents.power.energy_ram,
                harness.PerfEvents.power.energy_pkg,
            ]
        elif partition_name == config.CASCADE_LAKE:
            self.perf_events = [
                harness.PerfEvents.power.energy_cores,
                harness.PerfEvents.power.energy_ram,
                harness.PerfEvents.power.energy_pkg,
            ]
        else:
            self.perf_events = [
                harness.PerfEvents.power.energy_cores,
                harness.PerfEvents.power.energy_pkg,
            ]


@rfm.simple_test
class Weather_s(harness.SPEChpcBase, harness.FrequencySweepChosen, SetupPerfEvents):
    num_nodes = 1
    cpu_frequency = parameter([800 * F_MHZ, 900 * F_MHZ])
    spechpc_binary = fixture(harness.build_Weather_s, scope="environment")
    executable_opts = ["output6.test.txt", "2400", "1000", "750", "625", "1", "1", "6"]

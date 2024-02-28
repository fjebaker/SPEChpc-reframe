import logging

logging.basicConfig(level=logging.DEBUG)

import reframe as rfm
import reframe.core.builtins as blt

import harness
import harness.config as config

F_MHZ = config.F_MHZ

logger = logging.getLogger(__name__)


class SetupPerfEvents(rfm.RegressionMixin):
    """
    Helper mixin that selects the available perf events depending on the
    partition the job is being run on.
    """

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
class Weather_t(
    harness.SPEChpcBase,
    # enable perf instrumentation
    harness.PerfInstrument,
    # enable BMC database queries
    harness.BMCInstrument,
    # run as a frequency sweeping parameterized benchmark
    harness.FrequencySweepAll,
    # read in the perf events for the given environment
    SetupPerfEvents,
):
    num_nodes = 1
    # fixtures are used in order to re-use build products between multiple
    # benchmark runs
    spechpc_binary = fixture(
        harness.build_Weather_t,
        scope="environment",
        # for SPEChpc, the build environment needs to know the number of nodes
        # to determine the number of ranks
        variables={"spechpc_num_nodes": num_nodes},
    )
    # these options especially picked to run a very small test job
    executable_opts = ["output6.test.txt", "2400", "1000", "750", "625", "10", "1", "6"]

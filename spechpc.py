import logging

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


class BenchmarkBase(
    harness.SPEChpcBase,
    harness.PerfInstrument,
    harness.BMCInstrument,
    harness.FrequencySweepAll,
    SetupPerfEvents,
): ...


@rfm.simple_test
class Lbm_t(BenchmarkBase):
    num_nodes = 1
    spechpc_binary = fixture(
        harness.build_Lbm_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )


@rfm.simple_test
class Soma_t(BenchmarkBase):
    num_nodes = 1
    spechpc_binary = fixture(
        harness.build_Soma_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )
    # using these fixtures to ensure the build process is serial between tests
    dag_build = fixture(
        harness.build_Lbm_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )


@rfm.simple_test
class Tealeaf_t(BenchmarkBase):
    num_nodes = 1
    spechpc_binary = fixture(
        harness.build_Tealeaf_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )
    dag_build = fixture(
        harness.build_Soma_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )


@rfm.simple_test
class Clvleaf_t(BenchmarkBase):
    num_nodes = 1
    spechpc_binary = fixture(
        harness.build_Clvleaf_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )
    dag_build = fixture(
        harness.build_Tealeaf_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )


@rfm.simple_test
class Pot3d_t(BenchmarkBase):
    num_nodes = 1
    spechpc_binary = fixture(
        harness.build_Pot3d_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )
    dag_build = fixture(
        harness.build_Clvleaf_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )


@rfm.simple_test
class Hpgmgfv_Exa_t(BenchmarkBase):
    num_nodes = 1
    spechpc_binary = fixture(
        harness.build_Hpgmgfv_Exa_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )
    dag_build = fixture(
        harness.build_Pot3d_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )


@rfm.simple_test
class Weather_t(BenchmarkBase):
    num_nodes = 1
    spechpc_binary = fixture(
        harness.build_Weather_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )
    dag_build = fixture(
        harness.build_Hpgmgfv_Exa_t,
        scope="environment",
        variables={"spechpc_num_nodes": num_nodes},
    )

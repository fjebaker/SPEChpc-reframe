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
class Lbm_t(harness.SPEChpcBase, harness.FrequencySweepAll, SetupPerfEvents):
    num_nodes = 1
    spechpc_binary = fixture(harness.build_Lbm_t, scope="environment")


@rfm.simple_test
class Soma_t(harness.SPEChpcBase, harness.FrequencySweepAll, SetupPerfEvents):
    num_nodes = 1
    spechpc_binary = fixture(harness.build_Soma_t, scope="environment")
    # using these fixtures to ensure the build process is serial between tests
    dag_build = fixture(harness.build_Lbm_t, scope="environment")


@rfm.simple_test
class Tealeaf_t(harness.SPEChpcBase, harness.FrequencySweepAll, SetupPerfEvents):
    num_nodes = 1
    spechpc_binary = fixture(harness.build_Tealeaf_t, scope="environment")
    dag_build = fixture(harness.build_Soma_t, scope="environment")


@rfm.simple_test
class Clvleaf_t(harness.SPEChpcBase, harness.FrequencySweepAll, SetupPerfEvents):
    num_nodes = 1
    spechpc_binary = fixture(harness.build_Clvleaf_t, scope="environment")
    dag_build = fixture(harness.build_Tealeaf_t, scope="environment")


@rfm.simple_test
class Pot3d_t(harness.SPEChpcBase, harness.FrequencySweepAll, SetupPerfEvents):
    num_nodes = 1
    spechpc_binary = fixture(harness.build_Pot3d_t, scope="environment")
    dag_build = fixture(harness.build_Clvleaf_t, scope="environment")


@rfm.simple_test
class Hpgmgfv_Exa_t(harness.SPEChpcBase, harness.FrequencySweepAll, SetupPerfEvents):
    num_nodes = 1
    spechpc_binary = fixture(harness.build_Hpgmgfv_Exa_t, scope="environment")
    dag_build = fixture(harness.build_Pot3d_t, scope="environment")


@rfm.simple_test
class Weather_t(harness.SPEChpcBase, harness.FrequencySweepAll, SetupPerfEvents):
    num_nodes = 1
    spechpc_binary = fixture(harness.build_Weather_t, scope="environment")
    dag_build = fixture(harness.build_Hpgmgfv_Exa_t, scope="environment")


# can't seem to compile?
# @rfm.simple_test
# class Sph_Exa_t(harness.SPEChpcBase, harness.FrequencySweepAll, SetupPerfEvents):
#     num_nodes = 1
#     spechpc_binary = fixture(harness.build_Sph_Exa_t, scope="environment")
#     dag_build = fixture(harness.build_Pot3d_t, scope="environment")

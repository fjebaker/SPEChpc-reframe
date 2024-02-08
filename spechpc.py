import logging

import reframe as rfm

import harness

F_MHZ = harness.frequency.F_MHZ

logger = logging.getLogger(__name__)


@rfm.simple_test
class Weather_s(harness.SPEChpcBase, harness.FrequencySweepChosen):

    cpu_frequency = parameter([800 * F_MHZ, 900 * F_MHZ])

    perf_events = [
        harness.PerfEvents.power.energy_cores,
        harness.PerfEvents.power.energy_pkg,
    ]

    spechpc_binary = fixture(harness.build_Weather_s, scope="environment")

    executable_opts = ["output6.test.txt", "2400", "1000", "750", "625", "1", "1", "6"]
    num_nodes = 1

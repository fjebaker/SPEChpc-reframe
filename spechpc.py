import logging

import reframe as rfm

import harness

logger = logging.getLogger(__name__)


@rfm.simple_test
class Weather_s(harness.SPEChpcBase, harness.FrequencySweep):

    cpu_frequency = parameter([800, 900])  # mhz

    perf_events = [
        harness.PerfEvents.power.energy_cores,
        harness.PerfEvents.power.energy_pkg,
    ]

    spechpc_binary = fixture(harness.build_Weather_s, scope="environment")

    executable_opts = ["output6.test.txt", "2400", "1000", "750", "625", "1", "1", "6"]
    num_nodes = 1

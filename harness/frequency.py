import os
import logging

import reframe as rfm
import reframe.core.builtins as blt
import reframe.utility.sanity as sn

logger = logging.getLogger(__name__)


FREQUENCY_SET_DEBUG = os.environ.get("SRFM_FREQUENCY_DEBUG", None) is not None

if FREQUENCY_SET_DEBUG:
    logger.warn("FREQUENCY_SET_DEBUG is set. Will not attempt to set CPU frequencies.")

F_MHZ = 1
F_GHZ = 1000 * F_MHZ

FREQUENCY_LOOKUP = {
    "cclake": [
        2.20 * F_GHZ,
        2.20 * F_GHZ,
        2.10 * F_GHZ,
        2.00 * F_GHZ,
        1.90 * F_GHZ,
        1.80 * F_GHZ,
        1.70 * F_GHZ,
        1.60 * F_GHZ,
        1.50 * F_GHZ,
        1.40 * F_GHZ,
        1.30 * F_GHZ,
        1.20 * F_GHZ,
        1.10 * F_GHZ,
        1000 * F_MHZ,
    ],
    "sapphire": [
        2.00 * F_GHZ,
        2.00 * F_GHZ,
        1.90 * F_GHZ,
        1.80 * F_GHZ,
        1.70 * F_GHZ,
        1.60 * F_GHZ,
        1.50 * F_GHZ,
        1.40 * F_GHZ,
        1.30 * F_GHZ,
        1.20 * F_GHZ,
        1.10 * F_GHZ,
        1000 * F_MHZ,
        900 * F_MHZ,
        800 * F_MHZ,
    ],
    "icelake": [
        2.60 * F_GHZ,
        2.60 * F_GHZ,
        2.50 * F_GHZ,
        2.30 * F_GHZ,
        2.20 * F_GHZ,
        2.10 * F_GHZ,
        2.00 * F_GHZ,
        1.80 * F_GHZ,
        1.70 * F_GHZ,
        1.60 * F_GHZ,
        1.40 * F_GHZ,
        1.30 * F_GHZ,
        1.20 * F_GHZ,
        1.10 * F_GHZ,
        900 * F_MHZ,
        800 * F_MHZ,
    ],
    # fergus's test system
    "clusterlaine": [2.0 * F_GHZ, 1.0 * F_GHZ],
}

PARAMETER_CARDINALITY = max(len(v) for _, v in FREQUENCY_LOOKUP.items())


def partition_frequencies(name: str):
    fqs = FREQUENCY_LOOKUP.get(name, None)

    if fqs:
        return fqs

    raise ValueError(f"No frequencies for requested parititon {name}")


class FrequencyBase(rfm.RegressionMixin):
    def set_frequency_cmd(self) -> str:
        # todo: this is ridiculously unsafe and in an ideal world
        # the parameter would be sanitized but oh well !!!
        cmd = f"sudo cpupower frequency-set -f {self.cpu_frequency}mhz"
        if FREQUENCY_SET_DEBUG:
            return f'echo "{cmd}"'
        else:
            return cmd

    @blt.run_before("run", always_last=True)
    def set_cpu_frequency(self):
        if self.prerun_cmds:
            self.prerun_cmds.append(self.set_frequency_cmd())
        else:
            self.prerun_cmds = [self.set_frequency_cmd()]


class FrequencySweepAll(FrequencyBase):

    # hack: since parameters can't take specific values depending on partition
    # we run over all possible frequency indexes for each partition
    # and skip if the index is invalid
    cpu_frequency_index = parameter(range(PARAMETER_CARDINALITY))
    cpu_frequency = variable(float)

    @blt.run_after("setup")
    def get_frequency(self):
        frequency_list = partition_frequencies(self.current_partition.name)

        if self.cpu_frequency_index >= len(frequency_list):
            self.skip(
                msg=f"Parameter index is out of range ({self.cpu_frequency_index} >= {len(frequency_list)})"
            )

        self.cpu_frequency = frequency_list[self.cpu_frequency_index]


class FrequencySweepChosen(FrequencyBase):

    # must be overriden by subclass
    cpu_frequency = parameter()

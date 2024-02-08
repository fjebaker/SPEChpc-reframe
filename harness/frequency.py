import os
import logging

from harness.config import FREQUENCY_LOOKUP

import reframe as rfm
import reframe.core.builtins as blt
import reframe.utility.sanity as sn


logger = logging.getLogger(__name__)


FREQUENCY_SET_DEBUG = os.environ.get("SRFM_FREQUENCY_DEBUG", None) is not None

if FREQUENCY_SET_DEBUG:
    logger.warn("FREQUENCY_SET_DEBUG is set. Will not attempt to set CPU frequencies.")


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

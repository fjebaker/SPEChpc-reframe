import os
import logging

from harness.config import POWERCAP_LOOKUP

import reframe as rfm
import reframe.core.builtins as blt


logger = logging.getLogger(__name__)


POWERCAP_SET_DEBUG = os.environ.get("SRFM_NODE_SETUP_DEBUG", None) is not None

if POWERCAP_SET_DEBUG:
    logger.warn("SRFM_NODE_SETUP_DEBUG is set. Will not attempt to set power cap.")


PARAMETER_CARDINALITY = max(len(v) for _, v in POWERCAP_LOOKUP.items())


def partition_powercaps(name: str):
    fqs = POWERCAP_LOOKUP.get(name, None)

    if fqs:
        return fqs

    raise ValueError(f"No powercap for requested parititon {name}")


class PowercapBase(rfm.RegressionMixin):

    def powercap_cmd(self) -> str:
        # todo: this is ridiculously unsafe and in an ideal world
        # the parameter would be sanitized but oh well !!!
        cmd = f"sudo cpupower frequency-set -f {self.powercap_value}mhz"
        return cmd

    def _construct_cmd(self) -> str:
        cmd = self.powercap_cmd()

        # for multi-nodes, need to make sure it gets run on each node
        if self.num_nodes > 1:
            prefix = f"srun --ntasks-per-node=1 -n{self.num_nodes} -N{self.num_nodes}"
            cmd = prefix + " " + cmd

        if POWERCAP_SET_DEBUG:
            return f'echo "{cmd}"'
        else:
            return cmd

    @blt.run_before("run", always_last=True)
    def set_powercap_value(self):
        if self.prerun_cmds:
            self.prerun_cmds.append(self._construct_cmd())
        else:
            self.prerun_cmds = [self._construct_cmd()]


class PowercapSweepAll(PowercapBase):

    # hack: since parameters can't take specific values depending on partition
    # we run over all possible frequency indexes for each partition
    # and skip if the index is invalid
    powercap_index = parameter(range(PARAMETER_CARDINALITY))
    powercap_value = variable(float)

    @blt.run_after("setup")
    def get_powercap(self):
        powercap_list = partition_powercaps(self.current_partition.name)

        if self.powercap_index >= len(powercap_list):
            self.skip(
                msg=f"Parameter index is out of range ({self.powercap_index} >= {len(powercap_list)})"
            )

        self.cpu_frequency = powercap_list[self.powercap_index]

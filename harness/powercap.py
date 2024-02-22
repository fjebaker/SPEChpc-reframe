import os
import logging

from harness.config import POWERCAP_LOOKUP
import harness.utils as utils

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

    racadm_path = "/opt/dell/srvadmin/sbin/racadm"

    def powercap_cmd(self) -> list:
        # todo: this is ridiculously unsafe and in an ideal world
        # the parameter would be sanitized but oh well !!!
        cmds = [
            f"sudo {self.racadm_path} set system.power.cap.watts {self.powercap_value}",
            # give idrac a change to update
            "sleep 5",
            # write the configured value to a file
            f"sudo {self.racadm_path} get system.power.cap.watts > powercap_value",
            # then we validate to make sure the cap worked
            f'if [ $(head -n1 powercap_value | cut -d\' \' -f1) != "{self.powercap_value}" ]; then echo "Powercap mismatch" && exit 1; fi',
        ]

        return cmds

    def _construct_powercap_cmd(self) -> str:
        cmd = self.powercap_cmd()
        return utils.multiplex_for_each_node(cmd, self.num_nodes, POWERCAP_SET_DEBUG)

    @blt.run_before("run", always_last=True)
    def set_powercap_value(self):
        if self.prerun_cmds:
            self.prerun_cmds += self._construct_powercap_cmd()
        else:
            self.prerun_cmds = self._construct_powercap_cmd()


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

import reframe as rfm
import reframe.core.builtins as blt
import reframe.utility.sanity as sn

F_MHZ = 1000  # hz
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


class FrequencySweep(rfm.RegressionMixin):

    # derived must override this
    cpu_frequency = parameter()

    def set_frequency_cmd(self) -> str:
        # todo: this is ridiculously unsafe and in an ideal world
        # the parameter would be sanitized but oh well !!!
        return f"sudo cpupower frequency-set -f {self.cpu_frequency}mhz"

    @blt.run_before("run", always_last=True)
    def set_cpu_frequency(self):
        if self.prerun_cmds:
            self.prerun_cmds.append(self.set_frequency_cmd())
        else:
            self.prerun_cmds = [self.set_frequency_cmd()]

        print(self.prerun_cmds)

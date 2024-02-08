import reframe as rfm
import reframe.core.builtins as blt
import reframe.utility.sanity as sn


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

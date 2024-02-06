from reframe.core.launchers import JobLauncher

import reframe.utility.typecheck as typ


class _Power:
    energy_cores = "power/energy-cores/"
    energy_pkg = "power/energy-pkg/"
    energy_ram = "power/energy-ram/"


class PerfEvents:
    power = _Power()


MS_PER_SECOND = 1000


class PerfLauncherWrapper(JobLauncher):
    """
    Wraps a target launcher with perf commands, either before or after the
    launch command.
    """

    poll_interval = 10 * MS_PER_SECOND

    def __init__(self, target_launcher, perf_events: typ.List[str] = [], prefix=True):
        super().__init__()

        self.perf_command = ["perf", "stat"]
        self.perf_command += [
            # don't change the output of numbers depending on locale
            "--no-big-num",
            f"-I {self.poll_interval}",
            "--per-socket",
            "-a",
        ]
        self.perf_command += [f'-e "{i}"' for i in perf_events]
        self.prefix = prefix
        self._target_launcher = target_launcher

    def command(self, job):
        if self.prefix:
            return self.perf_command + self._target_launcher.command(job)
        else:
            return self._target_launcher.command(job) + self.perf_command

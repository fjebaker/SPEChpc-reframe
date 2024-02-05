from reframe.core.launchers import JobLauncher


class _Power:
    energy_cores = "power/energy-cores/"
    pkg = "power/energy-pkg/"


class PerfEvents:
    power = _Power()


class PerfLauncherWrapper(JobLauncher):
    """
    Wraps a target launcher with perf commands, either before or after the
    launch command.
    """

    def __init__(self, target_launcher, perf_events: list[str] = [], prefix=True):
        super().__init__()

        self.perf_command = ["perf", "stat"]
        self.perf_command += [f'-e "{i}"' for i in perf_events]
        self.prefix = prefix
        self._target_launcher = target_launcher

    def command(self, job):
        if self.prefix:
            return self.perf_command + self._target_launcher.command(job)
        else:
            return self._target_launcher.command(job) + self.perf_command

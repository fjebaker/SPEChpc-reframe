from reframe.core.launchers import JobLauncher

import reframe.utility.typecheck as typ


class _Power:
    energy_cores = "power/energy-cores/"
    energy_pkg = "power/energy-pkg/"
    energy_ram = "power/energy-ram/"


class PerfEvents:
    power = _Power()


MS_PER_SECOND = 1000


def _line_of_file(line, filename) -> str:
    return f'sed "{line}q;d" {filename}'


MPI_TASK_SEPERATOR = ":\\\n    "


class PerfLauncherWrapper(JobLauncher):
    """
    Wraps a target launcher with perf commands, either before or after the
    launch command.

    The `num_nodes` argument differentiates how the perf command is inserted
    into the launcher. For example, when it is 1, the wrapper is in
    `"single-node"` mode, and the perf command is inserted as e.g.

        perf stat [...] mpirun [...] ./a.out

    When it is >1, the wrapper is in `"multi-node"` mode, and instead an
    "Unusual MPI" job is launched

        mpirun \
            --host A -n 1 perf stat [...] ./a.out \
            --host B -n 1 perf stat [...] ./a.out \
            [...] ./a.out
    """

    poll_interval = 10 * MS_PER_SECOND

    def __init__(
        self,
        target_launcher,
        perf_events: typ.List[str],
        executable,
        executable_opts,
        num_nodes,
    ):
        super().__init__()

        self.perf_command = ["perf", "stat"]
        self.perf_command += [
            # don't change the output of numbers depending on locale
            "--no-big-num",
            f"-I {self.poll_interval}",
            "--per-socket",
            # ensure it is system wide
            "-a",
        ]
        self.perf_command += [f'-e "{i}"' for i in perf_events]
        self.executable = executable
        self.executable_opts = executable_opts
        self._target_launcher = target_launcher

        # avoid namespace conflicts with a subtly different name
        self.num_runtime_nodes = num_nodes

    def command(self, job):
        root = self._target_launcher.command(job)
        if self.num_runtime_nodes == 1:
            return self.perf_command + root
        else:
            # todo: this is so hacky. Using deep domain-specific insight i know
            # that this can never go wrong, and will delete any commits that
            # suggest the contrary

            # save the `-np` arg so we can paste it on at the end
            i = root.index("-np")
            np_arg = root[i : i + 2]
            # remove the `-np`
            root = root[0:i] + root[i + 2 :]

            # append some output ordering so we can work out which host does what
            # todo: these flags are MPI implementation specific and currently
            # these only work for Intel MPI
            root += ["-l", "-ordered-output"]

            for i in range(self.num_runtime_nodes):
                sed_cmd = _line_of_file(i + 1, "hostfile")
                perf_task = ["--host", f"$({sed_cmd})", "-n", "1"]
                perf_task += self.perf_command
                perf_task += [self.executable] + self.executable_opts

                root += perf_task + [MPI_TASK_SEPERATOR]

            reduced_tasks = int(np_arg[1]) - self.num_runtime_nodes
            return root + [np_arg[0], f"{reduced_tasks}"]

    def additional_prerun_cmds(self):
        if self.num_runtime_nodes == 1:
            return []
        else:
            # todo: this only works if slurm is the backing launcher. if it
            # ever runs under a different scheduler, will need to modify
            # todo: same kind of thing but about Intel MPI flags
            return [
                "srun hostname > hostfile",
            ]

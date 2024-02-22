import logging

import reframe.utility.typecheck as typ
import reframe.core.builtins as blt
import reframe as rfm

from reframe.core.launchers import JobLauncher

import harness.utils as utils

MS_PER_SECOND = 1000
MPI_TASK_SEPERATOR = ": \\\n    "

logger = logging.getLogger(__name__)


class _Power:
    energy_cores = "power/energy-cores/"
    energy_pkg = "power/energy-pkg/"
    energy_ram = "power/energy-ram/"


class PerfEvents:
    power = _Power()


def _line_of_file(line, filename) -> str:
    return f'sed "{line}q;d" {filename}'


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

            num_nodes = self.num_runtime_nodes
            return [
                f"srun --ntasks-per-node=1 -n{num_nodes} -N{num_nodes} hostname > hostfile",
            ]


class PerfInstrument(rfm.RegressionMixin):
    perf_events = variable(typ.List[str], value=[])

    # prefix all names with _perf_instrument_* to avoid namespace collisions
    def _perf_instrument_check_preconditions(self):
        if not self.executable:
            raise ValueError(
                "self.executable must be set before the PerfInstrument wrapper is invoked!"
            )

        if (not self.executable_opts) and (not type(self.executable_opts) is list):
            raise ValueError(
                "self.executable_opts must be set before the PerfInstrument wrapper is invoked!"
            )

        if not self.num_nodes:
            raise ValueError(
                "self.num_nodes must be set before the PerfInstrument wrapper is invoked!"
            )

        logger.info("Preconditions passed")

    @blt.run_before("run", always_last=True)
    def _perf_instrument_wrap_perf_launcher(self):
        self._perf_instrument_check_preconditions()

        logger.debug("perf events selected %s", self.perf_events)

        # use the perf wrapper only if we're measuring perf events
        if self.perf_events:
            self.job.launcher = PerfLauncherWrapper(
                self.job.launcher,
                self.perf_events,
                self.executable,
                self.executable_opts,
                self.num_nodes,
            )
            # get any additional pre-run commands
            self.prerun_cmds += self.job.launcher.additional_prerun_cmds()

    @blt.performance_function("J")
    def _perf_instrument_extract_perf_energy_event(
        self, key=None, socket=0, host_index=None
    ):
        if not key:
            raise ValueError("`key` has no value")

        if socket < 0:
            raise ValueError("`socket` cannot be negative")

        # todo: this could easily be a single query instead of two
        # if we hand roll the regex capture instead
        all_time_measurements = utils.extract_perf_values_for_host(
            socket, key, self.stderr, "time", host_index
        )
        all_energy_measurements = utils.extract_perf_values_for_host(
            socket, key, self.stderr, "energy", host_index
        )

        time_series_key = f"perf/{socket}/{key}"

        # use the host name if it's a mutli-node job
        if not host_index is None:
            node_name = self.job.nodelist[host_index]
            time_series_key = f"perf/{node_name}/{socket}/{key}"

        # save all measurements to the time series dictionary
        self.time_series[time_series_key] = [
            # explicitly call list, as the extraction functions return reframe
            # deferrables
            list(all_time_measurements),
            list(all_energy_measurements),
        ]

        # return the summed energy
        return sum(all_energy_measurements)

    @blt.run_before("performance", always_last=True)
    def _perf_instrument_set_variables(self):
        # build the selected perf events dictionary depending on the number of nodes
        if self.num_nodes == 1:
            perf_events_gather = {
                f"/{socket}/{k}": self._perf_instrument_extract_perf_energy_event(
                    k, socket
                )
                for k in self.perf_events
                for socket in range(self.current_partition.processor.num_sockets)
            }
        else:
            # for multi-node jobs, need to extract a perf value for each node
            perf_events_gather = {
                f"/{host}/{socket}/{k}": self._perf_instrument_extract_perf_energy_event(
                    k, socket, i, host
                )
                for k in self.perf_events
                for socket in range(self.current_partition.processor.num_sockets)
                for (i, host) in enumerate(self.job.nodelist)
            }

        logger.debug(
            "Perf events to be gathered: %s",
            [k for (k, v) in perf_events_gather.items()],
        )

        if self.perf_variables:
            self.perf_variables = {
                **perf_events_gather,
                **self.perf_variables,
            }
        else:
            self.perf_variables = perf_events_gather

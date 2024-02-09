import os
import logging
import pathlib

import reframe.utility.typecheck as typ

import reframe as rfm
import reframe.core.builtins as blt
from reframe.core.buildsystems import BuildSystem
from reframe.core.exceptions import BuildSystemError

import harness.utils as utils

logger = logging.getLogger(__name__)

GENERATED_CONFIG_NAME = "spechpc_config.cfg"
GENERATED_CONFIG_IN = "spechpc_config.cfg.in"
CONTORL_FILENAME = "control"


class SPEChpcBuild(BuildSystem):
    """
    Custom builder that wraps the `runhpc` and `specmake` command of `SPEChpc`.

    We make a few assumptions:
        - the SPEChpc suite has been installed as per the confluence notes
          (todo: reproduce here either as docs or as code?)
        - the directory layout of SPEChpc has in no way been modified
    """

    # spechpc specifics
    spechpc_dir = variable(str, type(None), value=None)
    spechpc_config = variable(str, type(None), value=None)
    spechpc_num_ranks = variable(int, type(None), value=None)
    spechpc_tune = variable(str, value="base")
    spechpc_flags = variable(typ.List[str], value=["--fake", "--loose"])
    spechpc_benchmark = variable(str)
    partition_name = variable(str)

    use_control_file: bool = True
    additional_inputs = None

    """
    The absolute path of the stage directory. Must be set before the compile
    step.
    """
    stagedir = variable(str, type(None), value=None)

    # set by the RegressionTest pipeline
    executable = variable(str, type(None), value=None)

    def _check_preconditions(self):
        if not self.spechpc_dir:
            raise BuildSystemError(
                "SPEChpc directory is not specified (use the"
                " build system's `spechpc_dir` variable)."
            )
        if not self.stagedir:
            raise BuildSystemError(
                "Attribute `stagedir` has not been forwarded to the" " build system."
            )

        if not self.spechpc_num_ranks:
            raise BuildSystemError(
                "Number of ranks not known by the build system. Ensure `spechpc_num_ranks` is set"
            )

        # todo: this technically should have been passed but somehow not always
        if not self.executable:
            raise BuildSystemError(
                "Congratulations. I don't know how you did it, but you did."
                " Anyway, do it again but make sure the build system knows"
                " what the executable is called:"
                " `build_system.executable = name`"
            )

    def _generate_spechpc_config(self, environ) -> str:
        """
        Returns the relative path to generated config file in the staging
        directory.
        """
        config_path_in = os.path.join(self.stagedir, GENERATED_CONFIG_IN)
        config_path_out = os.path.join(".", GENERATED_CONFIG_NAME)

        # get the compilers from the environment

        # todo: let reframe pick the defaults!

        cc = self._cc(environ) or "mpiicc"
        cxx = self._cxx(environ) or "mpiicpc"
        fcn = self._ftn(environ) or "mpiifort"

        # read the template
        content_in = pathlib.Path(config_path_in).read_text()
        content_out = (
            content_in.replace("${CC}", cc)
            .replace("${CXX}", cxx)
            .replace("${FC}", fcn)
            .replace("${OPTIMIZE}", "-O2 -xHOST")
        )

        # write the new content
        pathlib.Path(config_path_out).write_text(content_out)
        return config_path_out

    def _create_spechpc_build_command(self) -> str:
        cmd = ["runhpc"]
        cmd += self.spechpc_flags
        cmd += ["--size", "ref"]
        cmd += ["--tune", self.spechpc_tune]
        cmd += ["--config", self.spechpc_config]
        cmd += ["--ranks", str(self.spechpc_num_ranks)]
        cmd += [self.spechpc_benchmark]
        return " ".join(cmd)

    def _create_benchmark_build_dir(self) -> str:
        return os.path.join("benchspec", "HPC", self.spechpc_benchmark, "build")

    def _setup_spechpc(self) -> typ.List[str]:
        # each partition gets its own SPEChpc directory to avoid
        # concurrency issues
        spechpc_src_dir = self.spechpc_dir + "_" + self.partition_name
        config_dir = os.path.join(spechpc_src_dir, "config")

        comp_step = [
            # copy over the configuration
            f'cp "{self.spechpc_config}" "{config_dir}"',
            # change to the spechpc directory
            f'cd "{spechpc_src_dir}"',
            # source the requisite environment file
            "source shrc",
            # setup the build configuration
            self._create_spechpc_build_command(),
            # cd to the chosen benchmark directory
            f'cd "{self._create_benchmark_build_dir()}"',
            # a little bit of cheek to get into the right directory
            'BUILD_DIR="$(ls -d * | sort -n | head -n 1)"',
            'cd "$BUILD_DIR"',
            # save the identifier for later
            "RUNID=$(basename $(pwd) | cut -d. -f2)",
            # do the build
            "specmake",
            # copy the binary back
            f'cp "{self.executable}" "{self.stagedir}"',
            # copy the command specification back
            f'cd "../../run/run_{self.spechpc_tune}_ref_intel_mpi.$RUNID"',
        ]

        # some benchmarks don't actually have control files, so we need to
        # specify alternatives
        if self.use_control_file:
            comp_step += [f'cp "{CONTORL_FILENAME}" "{self.stagedir}"']

        if self.additional_inputs:
            comp_step += [f'cp "{f}" "{self.stagedir}"' for f in self.additional_inputs]

        comp_step += [
            # finally, return to staging dir
            f'cd "{self.stagedir}"',
        ]

        return comp_step

    def emit_build_commands(self, environ):
        self._check_preconditions()

        if not self.spechpc_config:
            logger.debug("Generating SPEChpc configuration from system environment")
            self.spechpc_config = self._generate_spechpc_config(environ)

        return self._setup_spechpc()


class build_SPEChpc_benchmark_Base(rfm.CompileOnlyRegressionTest):

    modules = ["rhel8/default-icl", "intel-oneapi-mkl/2022.1.0/intel/mngj3ad6"]

    build_system = SPEChpcBuild()
    sourcesdir = "../src/"

    # must be set by downstream classes
    spechpc_benchmark = variable(str)
    spechpc_dir = variable(str, type(None), value=None)
    additional_inputs = variable(typ.List[str], value=[])
    use_control_file = variable(bool, value=True)

    @blt.run_before("compile")
    def set_build_variables(self):
        if not self.spechpc_dir:
            self.spechpc_dir = utils.lookup_spechpc_root_dir(self.current_system.name)

        # build the executable name from the chosen benchmark
        self.executable = utils.benchmark_binary_name(self.spechpc_benchmark)

        # build system needs some additional info that reframe doesnt pass by
        # default
        self.build_system.spechpc_dir = self.spechpc_dir
        # apparently SPEChpc needs to know the ranks at compile time
        # so lets make sure that's known
        self.num_runtime_ranks = self.current_partition.processor.num_cpus
        self.build_system.spechpc_num_ranks = self.num_runtime_ranks
        self.build_system.partition_name = self.current_partition.name
        self.build_system.executable = self.executable
        self.build_system.stagedir = self.stagedir
        self.build_system.spechpc_benchmark = self.spechpc_benchmark
        self.build_system.additional_inputs = self.additional_inputs
        self.build_system.use_control_file = self.use_control_file

    @blt.sanity_function
    def validate_build(self):
        # todo: assert the binary has been copied into the stage directory
        return True

    @property
    def executable_path(self):
        return self.relpath(self.executable)

    def relpath(self, path):
        return os.path.join(self.stagedir, path)

    def read_executable_opts(self) -> typ.List[str]:
        """
        Reads the executable's default arguments from the SPEChpc generated
        control file.
        """
        if not self.use_control_file:
            # no arguments
            return []

        cmdpath = os.path.join(self.stagedir, CONTORL_FILENAME)
        logger.debug("Reading SPEChpc benchmark arguments from file: %s", cmdpath)
        return pathlib.Path(cmdpath).read_text().split()

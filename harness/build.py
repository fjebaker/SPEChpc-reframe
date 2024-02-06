import os
import logging
import pathlib

import reframe.utility.typecheck as typ

from reframe.core.buildsystems import BuildSystem
from reframe.core.exceptions import BuildSystemError

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
    spechpc_benchmark = variable(str, value="635.weather_s")
    spechpc_tune = variable(str, value="base")
    spechpc_flags = variable(typ.List[str], value=["--fake", "--loose"])

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
        cmd += ["--ranks", "8"]  # todo: make sure this is the same number as at runtime
        cmd += [self.spechpc_benchmark]
        return " ".join(cmd)

    def _create_benchmark_build_dir(self) -> str:
        return os.path.join(
            self.spechpc_dir, "benchspec", "HPC", self.spechpc_benchmark, "build"
        )

    def _setup_spechpc(self) -> typ.List[str]:
        config_dir = os.path.join(self.spechpc_dir, "config")

        return [
            # copy over the configuration
            f'cp "{self.spechpc_config}" "{config_dir}"',
            # change to the spechpc directory
            f'cd "{self.spechpc_dir}"',
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
            f'cp "{CONTORL_FILENAME}" "{self.stagedir}"',
            # finally, return to staging dir
            f'cd "{self.stagedir}"',
        ]

    def emit_build_commands(self, environ):
        self._check_preconditions()

        if not self.spechpc_config:
            logger.debug("Generating SPEChpc configuration from system environment")
            self.spechpc_config = self._generate_spechpc_config(environ)

        return self._setup_spechpc()

    def read_executable_opts(self) -> typ.List[str]:
        """
        Reads the executable's default arguments from the SPEChpc generated
        control file.
        """
        cmdpath = os.path.join(self.stagedir, CONTORL_FILENAME)
        logger.debug("Reading SPEChpc benchmark arguments from file: %s", cmdpath)
        return pathlib.Path(cmdpath).read_text().split()

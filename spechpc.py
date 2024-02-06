import os
import requests

import logging

import reframe as rfm
import reframe.core.builtins as blt
import reframe.utility.sanity as sn

import harness

logger = logging.getLogger(__name__)

# check the database endpoint is set
SRFM_PROMETHEUS_ADDRESS = os.environ.get("SRFM_PROMETHEUS_ADDRESS", None)

if not SRFM_PROMETHEUS_ADDRESS:
    logger.warn("No SRFM_PROMETHEUS_ADDRESS given. Cannot fetch PDU measurement estimate.")

def _benchmark_binary_name(benchmark_name: str) -> str:
    """
    Get the benchmark binary name from the benchmark specification. E.g.,
    "635.weather_s" becomes "weather".
    """
    return os.path.join(".", benchmark_name.split(".")[1].split("_")[0])

def _construct_pdu_query_chasis(jobname, jobtime):
    # todo: this query is hyper specific to the setup, and should ideally be
    # more flexible
    query_string = "query"
    query_string += (
        'sum(integrate(measurementsOutletSensorSignedValue'
        '{job="' + jobname + '",sensorType="activePower",'
        'instance_name=~"PDU-B-FR06|PDU-A-FR06",outletId="22"}'
        '[\'' + jobtime + '\'s]))'
    )
    return query_string

def _construct_pdu_query_node(jobname, cluster, hostname):
    query_string = "query"
    query_string += (
             'amperageProbeReading{job="' + jobname + '", '
             'amperageProbeLocationName="System Board Pwr Consumption", '
             'cluster="' + cluster + '", alias="' + hostname + '"}'
    )
    return query_string

def _fetch_pdu_measurement(jobname, cluster=None, jobtime=None, hostname=None):
    headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    }

    if jobtime:
        query_string = _construct_pdu_query_chasis(jobname, jobtime)
    elif cluster and hostname:
        query_string = _construct_pdu_query_node(jobname, cluster, hostname)
    else:
        logger.error("Cannot determine PDU query to fetch with")
        raise ValueError("`jobtime` or `cluster` and `hostname` must be passed as arguments")

    response = requests.post(f"http://{SRFM_PROMETHEUS_ADDRESS}/prometheus/api/v1/query", headers=headers, data=query_string)
    return response.content

@rfm.simple_test
class SPEChpc(rfm.RegressionTest):

    valid_systems = ["*"]
    valid_prog_environs = ["*"]

    build_system = harness.SPEChpcBuild()

    # todo: can we do this better?
    build_system.spechpc_dir = "/home/lilith/Developer/SPEChpc/hpc2021-1.1.7"
    # todo: this depends on the system. can we add it to the environ?
    perf_events = [
        harness.PerfEvents.power.energy_cores,
        harness.PerfEvents.power.energy_pkg,
    ]

    spectimes_path = variable(str, type(None), value="spectimes.txt")

    executable = _benchmark_binary_name(build_system.spechpc_benchmark)
    executable_opts = ["output6.test.txt", "2400", "1000", "750", "625", "1", "1", "6"]

    num_tasks = 12

    @blt.run_before("compile")
    def set_build_variables(self):
        self.build_system.executable = self.executable
        self.build_system.stagedir = self.stagedir

    @blt.run_before("run")
    def wrap_perf_events(self):

        # use the perf wrapper only if we're measuring perf events
        if self.perf_events:
            self.job.launcher = harness.PerfLauncherWrapper(
                self.job.launcher,
                self.perf_events,
                prefix=True,
            )

        if not self.executable_opts:
            # read the executable args from the build directory
            self.executable_opts = self.build_system.read_executable_opts()

    @blt.performance_function("J")
    def extract_perf_energy_event(self, key=None):
        if not key:
            raise ValueError("`key` has no value")
        return sn.extractsingle(rf"(\S+) \w+ {key}", self.stderr, 1, float)

    @blt.performance_function("s")
    def extract_core_time(self):
        return sn.extractsingle(r"Core time:\s+(\S+)", self.spectimes_path, 1, float)

    @blt.run_before("performance")
    def set_performance_variables(self):
        # build the selected perf events dictionary
        perf_events_gather = {
            k: self.extract_perf_energy_event(k) for k in self.perf_events
        }

        self.perf_variables = {
            **perf_events_gather,
            "Core time": self.extract_core_time(),
        }

        if SRFM_PROMETHEUS_ADDRESS:
            # todo: get the jobname and jobtime from the scheduler
            self.perf_variables["Energy PDU"] = self.fetch_pdu_measurements("some-job", 1)

    @blt.performance_function("J")
    def fetch_pdu_measurements(self, jobname=None, jobtime=None):
        # why do i need to give them default values??? the interpreter does
        # this for me
        if not jobname:
            raise ValueError("`jobname` has no value")
        if not jobtime:
            raise ValueError("`jobtime` has no value")

        return _fetch_pdu_measurement(jobname, jobtime=jobtime)

    @blt.sanity_function
    def assert_passed(self):
        return sn.assert_found(r"Verification: PASSED", self.spectimes_path)

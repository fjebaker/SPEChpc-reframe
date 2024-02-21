import os
import logging
import json

import requests
import numpy as np

import reframe as rfm
import reframe.core.builtins as blt
import reframe.utility.typecheck as typ

import harness.utils as utils

logger = logging.getLogger(__name__)

# check the database endpoint is set
SRFM_PROMETHEUS_ADDRESS = os.environ.get("SRFM_PROMETHEUS_ADDRESS", None)
SRFM_PROMETHEUS_TOKEN = os.environ.get("SRFM_PROMETHEUS_TOKEN", None)

# this switch is to prepare everything for the query, but not actually make it
# and instead just print to stdout
SRFM_PROMETHEUS_DEBUG_ONLY: bool = (
    os.environ.get("SRFM_PROMETHEUS_DEBUG_ONLY", None) is not None
)

DATABASE_QUERY_ENABLED: bool = (
    True
    if (
        # only do the query if we have all the information we need
        (SRFM_PROMETHEUS_ADDRESS and SRFM_PROMETHEUS_TOKEN)
        # or if debug mode is enabled, in which case the fetch is never made
        or SRFM_PROMETHEUS_DEBUG_ONLY
    )
    else False
)

STATUS_SUCCESS = "success"

# tell the user what they've got configured

if not DATABASE_QUERY_ENABLED:
    logger.warn(
        "No SRFM_PROMETHEUS_ADDRESS and/or SRFM_PROMETHEUS_TOKEN"
        " given. Cannot fetch PDU measurement estimate."
    )

if SRFM_PROMETHEUS_DEBUG_ONLY:
    logger.warn("SRFM_PROMETHEUS_DEBUG_ONLY is set. Fetch query will not be performed.")


def _digest_result(data: dict) -> np.array:
    if data["status"] != STATUS_SUCCESS:
        logger.error("Dabase returned status: %s", data["status"])
        raise ValueError("Database query returned unsuccessful!")

    return np.array(data["data"]["result"][0]["values"], dtype=np.float64)


CLUSTER_LOOKUP = {
    "sapphire": "Sapphire Rapid",
    "cclake": "Cascade Lake",
}


def _construct_pdu_query_node(cluster: str, nodename: str):
    # cluster name is capitalized in the database, so we make sure it is here too
    # for some others it has a special string so assert that with a lookup
    cluster_name = CLUSTER_LOOKUP.get(cluster, cluster.title())
    return (
        'amperageProbeReading{job="snmp_bmc", '
        'amperageProbeLocationName="System Board Pwr Consumption", '
        'cluster="' + cluster_name + '", alias="' + nodename + '"}'
    )


def _make_pdu_query(start_date: str, end_date: str, cluster, nodename):
    query_string = _construct_pdu_query_node(cluster, nodename)

    headers = {
        "Authorization": f"Bearer {SRFM_PROMETHEUS_TOKEN}",
        "Accept": "application/json",
    }

    data = {
        "query": query_string,
        "start": start_date,
        "end": end_date,
        "step": "60s",
    }

    if SRFM_PROMETHEUS_DEBUG_ONLY:
        # todo: log to debug? but then have to mess with levels?
        logger.warn("request data: %s", json.dumps(data, indent=2))
        return np.zeros((1, 2), dtype=np.float64)
    else:
        response = requests.post(
            f"http://{SRFM_PROMETHEUS_ADDRESS}/api/v1/query_range",
            headers=headers,
            data=data,
            timeout=10,
        )

        result = json.loads(response.content.decode())
        return _digest_result(result)


def fetch_pdu_measurements(
    start_time: str,
    end_time: str,
    cluster: str,
    nodename: str,
) -> np.array:
    """
    Units of the query are [['s', 'W'], ...]
    """
    return _make_pdu_query(
        start_time,
        end_time,
        cluster,
        nodename,
    )


class BMCInstrument(rfm.RegressionMixin):

    # database specifics
    job_start_time = variable(str, type(None), value=None)
    job_end_time = variable(str, type(None), value=None)
    database_query_node_names = variable(typ.List[str], type(None), value=None)

    cooldown_seconds = variable(int, value=60)

    @blt.run_before("run", always_last=True)
    def _bmc_instrument_post_command(self):
        postrun_cmds = [
            # after the run has finished and all measurements are made
            # rest the node for a bit before the next job sweeps in so
            # the database measurements are sane
            f'echo "Sleeping for {self.cooldown_seconds} seconds"',
            f"sleep {self.cooldown_seconds}s",
        ]

        if self.postrun_cmds:
            self.postrun_cmds += postrun_cmds
        else:
            self.postrun_cmds = postrun_cmds

    @blt.run_after("run", always_last=True)
    def _bmc_instrument_scheduler_times(self):
        # for the database query, need a rough estimate of when to start query
        self.job_end_time = utils.time_now(False)

        # can we get a better estimate from the scheduler?
        maybe_better_times = utils.query_runtime(self.job)
        if maybe_better_times:
            self.job_start_time = maybe_better_times[0]
            self.job_end_time = maybe_better_times[1]

        # adjust the cooldown period in the recorded end time
        self.job_end_time = utils.subtract_cooldown(
            self.job_end_time, self.cooldown_seconds
        )

        # after the run we ask the job where it ran
        if self.job.nodelist:
            logger.debug("Nodelist for job %s: %s", self.job.jobid, self.job.nodelist)
            self.database_query_node_names = self.job.nodelist
        else:
            logger.warn("No nodelists set by scheduler. Cannot query database")

    @blt.performance_function("J")
    def _bmc_instrument_extract_database_readings(self, nodename=None):
        if not nodename:
            raise ValueError("`nodename` must be defined")

        # get the pdu measurements
        values = fetch_pdu_measurements(
            self.job_start_time,
            self.job_end_time,
            self.partition_name,
            nodename,
        )

        time_values = values[:, 0]
        power_values = values[:, 1]

        self.time_series[f"BMC/{nodename}"] = [
            list(time_values),
            list(power_values),
        ]

        # integrate under the power curve to get the total energy
        return np.trapz(power_values, time_values)

    @blt.run_before("performance", always_last=True)
    def _bmc_instrument_set_performance_variables(self):
        logger.debug("Nodelist for database query: %s", self.database_query_node_names)

        # if database is enabled, add those performance variables too
        if DATABASE_QUERY_ENABLED:
            bmc_variables = {}
            for nodename in self.database_query_node_names:
                bmc_variables[f"BMC/{nodename}"] = (
                    self._bmc_instrument_extract_database_readings(nodename)
                )

            if self.perf_variables:
                self.perf_variables = {**self.perf_variables, **bmc_variables}
            else:
                self.perf_variables = bmc_variables

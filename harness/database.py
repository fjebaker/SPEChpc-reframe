import os
import logging

import requests

import reframe.core.builtins as blt
import reframe.utility.sanity as sn

logger = logging.getLogger(__name__)

# check the database endpoint is set
SRFM_PROMETHEUS_ADDRESS = os.environ.get("SRFM_PROMETHEUS_ADDRESS", None)

if not SRFM_PROMETHEUS_ADDRESS:
    logger.warn(
        "No SRFM_PROMETHEUS_ADDRESS given. Cannot fetch PDU measurement estimate."
    )


def _construct_pdu_query_chasis(jobname, jobtime):
    # todo: this query is hyper specific to the setup, and should ideally be
    # more flexible
    query_string = "query"
    query_string += (
        "sum(integrate(measurementsOutletSensorSignedValue"
        '{job="' + jobname + '",sensorType="activePower",'
        'instance_name=~"PDU-B-FR06|PDU-A-FR06",outletId="22"}'
        "['" + jobtime + "'s]))"
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


def _make_pdu_query(jobname, cluster=None, jobtime=None, hostname=None):
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    if jobtime:
        query_string = _construct_pdu_query_chasis(jobname, jobtime)
    elif cluster and hostname:
        query_string = _construct_pdu_query_node(jobname, cluster, hostname)
    else:
        logger.error("Cannot determine PDU query to fetch with")
        raise ValueError(
            "`jobtime` or `cluster` and `hostname` must be passed as arguments"
        )

    response = requests.post(
        f"http://{SRFM_PROMETHEUS_ADDRESS}/prometheus/api/v1/query",
        headers=headers,
        data=query_string,
    )
    return response.content


def fetch_pdu_measurements(jobname, jobtime):
    if SRFM_PROMETHEUS_ADDRESS:
        # todo: get the jobname and jobtime etc from the scheduler
        return {
            "Energy PDU": sn.make_performance_function(
                _make_pdu_query, "J", jobname, jobtime=jobtime
            )
        }

    return {}

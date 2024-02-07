import os
import logging
import datetime
import json

import requests

import reframe.utility.sanity as sn

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

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
DATETIME_QUERY_DELTA = datetime.timedelta(seconds=30)

# tell the user what they've got configured

if not DATABASE_QUERY_ENABLED:
    logger.warn(
        "No SRFM_PROMETHEUS_ADDRESS and/or SRFM_PROMETHEUS_TOKEN"
        " given. Cannot fetch PDU measurement estimate."
    )

if SRFM_PROMETHEUS_DEBUG_ONLY:
    logger.warn("SRFM_PROMETHEUS_DEBUG_ONLY is set. Fetch query will not be performed.")


def _construct_pdu_query_node(cluster, nodename):
    return (
        'amperageProbeReading{job="snmp_bmc", '
        'amperageProbeLocationName="System Board Pwr Consumption", '
        'cluster="' + cluster + '", alias="' + nodename + '"}'
    )


def _make_pdu_query(
    start_date: datetime.datetime, end_date: datetime.datetime, cluster, nodename
):
    query_string = _construct_pdu_query_node(cluster, nodename)

    headers = {
        "Authorization": f"Bearer {SRFM_PROMETHEUS_TOKEN}",
        "Accept": "application/json",
    }

    data = {
        "query": query_string,
        "start": start_date.strftime(DATETIME_FORMAT),
        "end": end_date.strftime(DATETIME_FORMAT),
        "step": "60s",
    }

    if SRFM_PROMETHEUS_DEBUG_ONLY:
        # todo: log to debug? but then have to mess with levels?
        logger.warn("request data: %s", json.dumps(data, indent=2))
        return 0
    else:
        response = requests.post(
            f"http://{SRFM_PROMETHEUS_ADDRESS}/prometheus/api/v1/query",
            headers=headers,
            data=data,
        )

        # todo: actually read out values here
        _ = json.loads(response.content)
        return 0


def get_query_time(start: bool = True) -> datetime.datetime:
    if start:
        return datetime.datetime.now() - DATETIME_QUERY_DELTA
    else:
        return datetime.datetime.now() + DATETIME_QUERY_DELTA


def fetch_pdu_measurements(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    cluster: str,
    nodename: str,
) -> dict:
    if DATABASE_QUERY_ENABLED:
        # todo: get the jobname and jobtime etc from the scheduler
        return {
            f"Energy PDU {nodename}": sn.make_performance_function(
                _make_pdu_query,
                "J",
                start_time,
                end_time,
                cluster,
                nodename,
            )
        }

    return {}

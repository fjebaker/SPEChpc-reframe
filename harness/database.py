import os
import logging
import datetime
import json

import requests
import numpy as np


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


def _construct_pdu_query_node(cluster: str, nodename: str):
    return (
        'amperageProbeReading{job="snmp_bmc", '
        'amperageProbeLocationName="System Board Pwr Consumption", '
        # cluster name is capitalized in the database, so we make sure it is here too
        'cluster="' + cluster.title() + '", alias="' + nodename + '"}'
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

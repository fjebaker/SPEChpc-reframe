import logging
import os
import re
import datetime

import reframe.utility.osext as osext
import reframe.utility.sanity as sn

logger = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
DATETIME_QUERY_DELTA = datetime.timedelta(seconds=5)

SPECHPC_ROOT_LOOKUP = {
    "personal": "/home/lilith/Developer/SPEChpc/hpc2021-1.1.7",
    "csd3-power-scaling": "/rds/user/fb609/hpc-work/SPEChpc/hpc2021-1.1.7",
}


def lookup_spechpc_root_dir(cluster_name: str) -> str:
    return SPECHPC_ROOT_LOOKUP[cluster_name]


def benchmark_binary_name(benchmark_name: str) -> str:
    """
    Get the benchmark binary name from the benchmark specification. E.g.,
    "635.weather_s" becomes "weather".
    """
    return os.path.join(".", benchmark_name.split(".")[1].split("_")[0])


def extract_perf_values(socket, key, fd, group):
    return sn.extractall(
        rf"(?P<time>\S+)\s+S{socket}\s+\d+\s+(?P<energy>\S+) \w+ {key}",
        fd,
        group,
        float,
    )


def query_runtime(job):
    # check we have slurm
    if job.scheduler.registered_name != "slurm":
        logger.info("Job does not use slurm. Cannot query better start / end time estimate.")
        return None

    slurm_query = [
        "sacct",
        "--format=start,end,elapsed",
        "--jobs=" + job.jobid,
        "--name=" + job.name,
    ]

    logger.info("Querying slurm for start / end time of jobid %s", job.jobid)
    logger.debug("Executing: '%s'", slurm_query)

    shell_exec = osext.run_command(slurm_query, check=True)
    # pull out the information we are interested in
    matches = re.finditer(
        r"^(?P<jobid>\S+)\s+(?P<start>\S+) (?P<end>\S+).*",
        shell_exec.stdout,
        re.MULTILINE,
    )

    for match in matches:
        if match.group("jobid") == job.jobid:
            start_time = match.group("start")
            end_time = match.group("end")

            logger.debug(
                "Start time %s end time %s for job %s", start_time, end_time, job.jobid
            )

            # todo: making the absolutely heinous asumption that the format of
            # the time is the same as in the database and we do absolutely
            # nothing to check that
            return start_time, end_time

    raise ValueError(f"Could not determine start / end time for job {job.jobid}")


def format_date(date: datetime.datetime) -> str:
    return date.strftime(DATETIME_FORMAT)


def time_now(start: bool = True) -> str:
    date = datetime.datetime.now()

    if start:
        date = date - DATETIME_QUERY_DELTA
    else:
        date = date + DATETIME_QUERY_DELTA

    return format_date(date)
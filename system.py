# configuration for CSD3
# modified from https://github.com/ukri-excalibur/excalibur-tests/blob/main/benchmarks/reframe_config.py

ICELAKE_PROC = {
    "num_cpus": 76,
    "num_cpus_per_core": 1,
    "num_sockets": 2,
    "num_cpus_per_socket": 38,
}

SAPPHIRE_RAPID_PROC = {
    "num_cpus": 112,
    "num_cpus_per_core": 1,
    "num_sockets": 2,
    "num_cpus_per_socket": 56,
}

CASCADE_LAKE_PROC = {
    "num_cpus": 56,
    "num_cpus_per_core": 1,
    "num_sockets": 2,
    "num_cpus_per_socket": 28,
}


def _make_access(account, reservation, nodelist):
    return [
        "--reservation=" + reservation,
        "--account=" + account,
        "--nodelist=" + nodelist,
    ]


def power_scaling_access(reservation, nodelist):
    return _make_access("SUPPORT-CPU", reservation, nodelist)


def geopm_access(reservation, nodelist):
    return _make_access("ZETTASCALE-ENERGY-SL2-CPU", reservation, nodelist)


def make_partition(name, descr, proc, access):
    return {
        "name": name,
        "descr": descr,
        "scheduler": "slurm",
        "launcher": "mpirun",
        "env_vars": [],
        "access": [
            "--partition=" + name,
            "--exclusive",
            *access,
        ],
        "sched_options": {
            "job_submit_timeout": 120,
            "use_nodes_options": True,
        },
        "environs": ["gcc", "intel"],
        "max_jobs": 64,
        "processor": proc,
    }


site_configuration = {
    "systems": [
        {
            "name": "csd3-power-scaling",
            "descr": "",
            "hostnames": ["login-q-1"],
            "modules_system": "tmod4",
            "partitions": [
                make_partition(
                    "icelake",
                    "",
                    ICELAKE_PROC,
                    power_scaling_access("downclock-perf-testing-1", "cpu-q-[3,4]"),
                ),
                make_partition(
                    "sapphire",
                    "",
                    SAPPHIRE_RAPID_PROC,
                    power_scaling_access("downclock-perf-testing-2", "cpu-r-[3,4]"),
                ),
                make_partition(
                    "cclake",
                    "",
                    CASCADE_LAKE_PROC,
                    power_scaling_access("downclock-perf-testing-3", "cpu-p-[471,472]"),
                ),
            ],
        },
        {
            "name": "csd3-geopm",
            "descr": "",
            "hostnames": ["login-q-1"],
            "modules_system": "tmod4",
            "partitions": [
                make_partition(
                    "icelake",
                    "",
                    ICELAKE_PROC,
                    geopm_access("geopm_i_ZL-451", "cpu-q-607"),
                ),
                make_partition(
                    "sapphire",
                    "",
                    SAPPHIRE_RAPID_PROC,
                    geopm_access("geopm_s_ZL-451", "cpu-r-110"),
                ),
            ],
        },
    ],
    "environments": [
        {
            "name": "intel",
            "cc": "mpiicc",
            "cxx": "mpiicpc",
            "ftn": "mpiifort",
            "modules": [],
        },
        {
            "name": "gcc",
            "cc": "mpicc",
            "cxx": "mpicxx",
            "ftn": "mpif90",
            "modules": [],
        },
    ],
}

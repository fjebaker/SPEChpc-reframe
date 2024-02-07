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


def make_partition(name, descr, proc):
    return {
        "name": name,
        "descr": descr,
        "scheduler": "slurm",
        "launcher": "mpirun",
        "env_vars": [
            [
                "I_MPI_PMI_LIBRARY",
                "/usr/local/software/slurm/current-rhel8/lib/libpmi2.so",
            ],
            ["I_MPI_OFI_PROVIDER", "mlx"],
            ["UCX_NET_DEVICES", "mlx5_0:1"],
        ],
        "access": ["--partition=" + name, "--exclusive"],
        "sched_options": {
            "job_submit_timeout": 120,
        },
        "environs": ["gcc", "intel"],
        "max_jobs": 64,
        "processor": proc,
    }


site_configuration = {
    "systems": [
        {
            "name": "GEOPM-reservation",
            "descr": "",
            "hostnames": ["login-q-1"],
            "modules_system": "tmod4",
            "partitions": [
                make_partition("icelake", "", ICELAKE_PROC),
                make_partition("sapphire", "", SAPPHIRE_RAPID_PROC),
            ],
        }
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

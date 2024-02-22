SPECHPC_ROOT_LOOKUP = {
    "personal": "/home/lilith/Developer/SPEChpc/hpc2021-1.1.7",
    "csd3-power-scaling": "/rds/user/fb609/hpc-work/SPEChpc/hpc2021-1.1.7",
}

F_MHZ = 1.0
F_GHZ = 1000.0 * F_MHZ

SAPPHIRE = "sapphire"
ICELAKE = "icelake"
CASCADE_LAKE = "cclake"

FREQUENCY_LOOKUP = {
    "cclake": [
        2.20 * F_GHZ,
        2.10 * F_GHZ,
        2.00 * F_GHZ,
        1.90 * F_GHZ,
        1.80 * F_GHZ,
        1.70 * F_GHZ,
        1.60 * F_GHZ,
        1.50 * F_GHZ,
        1.40 * F_GHZ,
        1.30 * F_GHZ,
        1.20 * F_GHZ,
        1.10 * F_GHZ,
        1000.0 * F_MHZ,
    ],
    "sapphire": [
        2.00 * F_GHZ,
        1.90 * F_GHZ,
        1.80 * F_GHZ,
        1.70 * F_GHZ,
        1.60 * F_GHZ,
        1.50 * F_GHZ,
        1.40 * F_GHZ,
        1.30 * F_GHZ,
        1.20 * F_GHZ,
        1.10 * F_GHZ,
        1000.0 * F_MHZ,
        900.0 * F_MHZ,
        800.0 * F_MHZ,
    ],
    "icelake": [
        2.60 * F_GHZ,
        2.50 * F_GHZ,
        2.30 * F_GHZ,
        2.20 * F_GHZ,
        2.10 * F_GHZ,
        2.00 * F_GHZ,
        1.80 * F_GHZ,
        1.70 * F_GHZ,
        1.60 * F_GHZ,
        1.40 * F_GHZ,
        1.30 * F_GHZ,
        1.20 * F_GHZ,
        1.10 * F_GHZ,
        900.0 * F_MHZ,
        800.0 * F_MHZ,
    ],
    # fergus's test system
    "clusterlaine": [2.0 * F_GHZ, 1.0 * F_GHZ],
}


def _powersteps(high, low, interval=50) -> list:
    items = []

    current = high
    while current >= low:
        items.append(current)
        current = current - interval

    return items


POWERCAP_LOOKUP = {
    # all units in watts
    "icelake": _powersteps(650, 250),
    "cclake": _powersteps(350, 150),
    "sapphire": _powersteps(1200, 550),
    # fergus's test system
    "clusterlaine": [1, 2],
}

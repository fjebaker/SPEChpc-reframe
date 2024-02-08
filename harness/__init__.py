from harness.build import SPEChpcBuild, build_SPEChpc_benchmark_Base
from harness.perf import PerfLauncherWrapper, PerfEvents
from harness.database import (
    fetch_pdu_measurements,
    DATABASE_QUERY_ENABLED,
)
from harness.base import SPEChpcBase

from harness.frequency import FrequencySweepAll, FrequencySweepChosen


class build_Weather_s(build_SPEChpc_benchmark_Base):
    spechpc_benchmark = "635.weather_s"

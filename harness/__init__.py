from harness.build import SPEChpcBuild, build_SPEChpc_benchmark_Base
from harness.perf import PerfEvents, PerfInstrument
from harness.database import (
    fetch_pdu_measurements,
    DATABASE_QUERY_ENABLED,
)
from harness.base import SPEChpcBase

from harness.frequency import (
    FrequencySweepAll,
    FrequencySweepChosen,
    FrequencyCPUGovenor,
)

# small


class build_Weather_s(build_SPEChpc_benchmark_Base):
    spechpc_benchmark = "635.weather_s"


# tiny


class build_Weather_t(build_SPEChpc_benchmark_Base):
    spechpc_benchmark = "535.weather_t"


class build_Lbm_t(build_SPEChpc_benchmark_Base):
    spechpc_benchmark = "505.lbm_t"
    additional_inputs = ["control"]


class build_Soma_t(build_SPEChpc_benchmark_Base):
    spechpc_benchmark = "513.soma_t"


class build_Tealeaf_t(build_SPEChpc_benchmark_Base):
    spechpc_benchmark = "518.tealeaf_t"
    use_control_file = False
    additional_inputs = ["tea.in", "tea.problems"]


class build_Clvleaf_t(build_SPEChpc_benchmark_Base):
    spechpc_benchmark = "519.clvleaf_t"
    use_control_file = False
    additional_inputs = ["clover.in"]


class build_Pot3d_t(build_SPEChpc_benchmark_Base):
    spechpc_benchmark = "528.pot3d_t"
    additional_inputs = ["pot3d1.dat", "br_input_small.h5"]


class build_Sph_Exa_t(build_SPEChpc_benchmark_Base):
    spechpc_benchmark = "532.sph_exa_t"


class build_Hpgmgfv_Exa_t(build_SPEChpc_benchmark_Base):
    spechpc_benchmark = "534.hpgmgfv_t"

from forensicstack.core.normalizers.exiftool_normalizer import ExiftoolNormalizer
from forensicstack.core.normalizers.ileapp_normalizer import ILEAPPNormalizer
from forensicstack.core.normalizers.aleapp_normalizer import ALEAPPNormalizer
from forensicstack.core.normalizers.volatility_normalizer import VolatilityNormalizer
from forensicstack.core.normalizers.eztools_normalizer import EZToolsNormalizer


NORMALIZER_REGISTRY = {
    "exiftool": ExiftoolNormalizer(),
    "ileapp": ILEAPPNormalizer(),
    "aleapp": ALEAPPNormalizer(),
    "volatility": VolatilityNormalizer(),
    "eztools": EZToolsNormalizer(),
}


def normalize(tool_name: str, output_dir: str):

    if tool_name not in NORMALIZER_REGISTRY:
        raise Exception("No normalizer registered")

    return NORMALIZER_REGISTRY[tool_name].normalize(output_dir)
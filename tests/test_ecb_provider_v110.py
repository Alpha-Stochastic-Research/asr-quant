import numpy as np

import asrquant as asr


def test_ecb_csv_parser_percent_conversion():
    csv = "TIME_PERIOD,OBS_VALUE,UNIT\n2026-08-07,2.50,PCPA\n2026-08-10,2.55,PCPA\n"
    frame = asr.ECBProvider._parse_csv(csv, percent_to_decimal=True)
    assert list(frame.columns) == ["Value"]
    assert np.isclose(frame.iloc[-1, 0], 0.0255)
    assert str(frame.index.tz) == "UTC"


def test_ecb_curve_key_and_provider_registry():
    assert asr.ECBProvider.yield_curve_key("10Y").endswith("SR_10Y")
    assert asr.ECBProvider.yield_curve_key("IF_1Y").endswith("IF_1Y")
    provider = asr.get_provider("ecb")
    assert isinstance(provider, asr.ECBProvider)

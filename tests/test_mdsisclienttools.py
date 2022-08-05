from mdsisclienttools import mdsisclienttools
from mdsisclienttools.auth.TokenManager import DeviceFlowManager


def test_fake() -> None:
    result = mdsisclienttools.fake_function()
    assert False

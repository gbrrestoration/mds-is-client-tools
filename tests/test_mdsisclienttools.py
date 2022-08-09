import pytest
from mdsisclienttools.auth.TokenManager import BearerAuth, DeviceFlowManager
import mdsisclienttools.datastore.ReadWriteHelper as IOHelper # type: ignore

IOHelper.DEFAULT_DATA_STORE_ENDPOINT = "https://data-api.testing.rrap-is.com"
auth_server = "https://auth.dev.rrap-is.com/auth/realms/rrap"

def test_fake()->None:
    assert True

@pytest.fixture
def init_auth_token()->DeviceFlowManager:
    local_token_storage = ".tokens.json"
    token_manager =  DeviceFlowManager(
        stage="TEST",
        keycloak_endpoint=auth_server,
        local_storage_location=local_token_storage
    )
    return token_manager

def test_get_handle(init_auth_token: DeviceFlowManager)->None:
    auth = init_auth_token.get_auth
    handle_id = "10378.1/1688092"
    IOHelper.download('./Data',handle_id,auth())

def test_read_auth( init_auth_token: DeviceFlowManager)->None:
    auth = init_auth_token.get_auth
    handle_id = "10378.1/1688092"
    assert IOHelper._read_dataset(handle_id,auth())

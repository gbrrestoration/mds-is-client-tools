import pytest
import requests
import json
from mdsisclienttools.auth.TokenManager import BearerAuth, DeviceFlowManager
import mdsisclienttools.datastore.ReadWriteHelper as IOHelper

IOHelper.DEFAULT_DATA_STORE_ENDPOINT = "https://data-api.testing.rrap-is.com"
auth_server = "https://auth.dev.rrap-is.com/auth/realms/rrap"
# handle_id = "10378.1/1687877"
handle_id = "10378.1/1688315"

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
    
@pytest.mark.dependency(depends=["test_item_exists", "test_upload_data"])
def test_download_data(init_auth_token: DeviceFlowManager)->None:
    auth = init_auth_token.get_auth
    IOHelper.download('./Data',handle_id, auth(), IOHelper.DEFAULT_DATA_STORE_ENDPOINT)

@pytest.mark.dependency(depends=["test_item_exists"])
def test_upload_data(init_auth_token: DeviceFlowManager)->None:
    auth = init_auth_token.get_auth
    IOHelper.upload(handle_id, auth(), "./data", IOHelper.DEFAULT_DATA_STORE_ENDPOINT)

def test_item_exists(init_auth_token: DeviceFlowManager)->None:
    auth = init_auth_token.get_auth
    postfix = "/registry/items/list-all-datasets"
    endpoint = IOHelper.DEFAULT_DATA_STORE_ENDPOINT + postfix 
    response = requests.get(endpoint, auth=auth())
    reg_items = response.json()['registry_items']
    assert any( item['handle'] == handle_id for item in reg_items)
    
    # print(json.dumps(response.json(), indent=2))
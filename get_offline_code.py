import requests
import time
import webbrowser
from typing import List
import os

"""
Contained in this script are basic device OAuth flows against a
keycloak server used to gain OIDC tokens which can be used to 
create temporary access credentials and temporary console sessions.
"""


def initiate_device_auth_flow(client_id: str, device_endpoint: str, scopes: List[str]):
    """Initiates an OAuth device authorization flow against
    the keycloak server. The client id and scope are included.

    Args:
        client_id (str): The client id desired for the 
        authorization flow - this is linked to the role 
        ARN that the IAM identity provider relationship 
        is allowed to authorize.

    Returns:
        Dict: The JSON response from the keycloak endpoint.
    """
    endpoint = device_endpoint
    data = {
        "client_id": client_id,
        "scope": ' '.join(scopes)
    }
    response = requests.post(endpoint, data=data).json()
    return response


def display_device_auth_flow(user_code: str, verification_url: str):
    """Given the user code and verification url from the device 
    auth challenge, will display in the console the URL and also
    open a browser window using the default browser defined in the 
    OS to the specified URL.

    Args:
        user_code (str): The device auth flow user code.
        verification_url (str): The verification URL with the user code embedded
    """
    print(f"Verification URL: {verification_url}")
    print(f"User Code: {user_code}")
    try:
        webbrowser.open(verification_url)
    except Exception:
        print("Tried to open web-browser but failed. Please visit URL above.")


def await_device_auth_flow_completion(device_code: str, client_id: str, interval: int, grant_type: str, scopes: List[str], token_endpoint: str):
    """Given the device code, client id and the poll interval, will 
    repeatedly post against the OAuth token endpoint to try and get
    an access and id token. Will wait until the user verifies at the 
    URL.

    Args:
        device_code (str): The oauth device code
        client_id (str): The keycloak client id
        interval (int): The polling interval returned from the 
        device auth flow endpoint.

    Returns:
        Dict: The response from the token endpoint (tokens)
    """
    # set up request
    data = {
        "grant_type": grant_type,
        "device_code": device_code,
        "client_id": client_id,
        "scope": " ".join(scopes)
    }
    endpoint = token_endpoint

    # Setup success criteria
    succeeded = False
    timed_out = False
    misc_fail = False

    # start time
    response_data = None

    # get requests session for repeated queries
    session = requests.session()

    # Poll for success
    while not succeeded and not timed_out and not misc_fail:
        response = session.post(endpoint, data=data)
        response_data = response.json()
        if response_data.get('error'):
            error = response_data['error']
            if error != 'authorization_pending':
                misc_fail = True
            # Wait appropriate OAuth poll interval
            time.sleep(interval)
        else:
            # Successful as there was no error at the endpoint
            return response_data

    try:
        print(f"Failed due to {response_data['error']}")
        return None
    except Exception as e:
        print(
            f"Failed with unknown error, failed to find error message. Error {e}")
        return None


def generate_offline_access_token(export_to_env : bool = False) -> None:
    # OIDC client ids
    client_id = "automated-access"

    # grant type
    device_grant_type = "urn:ietf:params:oauth:grant-type:device_code"

    # grant scope
    scopes = ["offline_access", "roles"]

    # Base auth URL
    base_url = "https://auth.rrap-is.com/auth/realms/rrap/"

    # oidc auth endpoint
    oidc_device_auth_endpoint = base_url + "protocol/openid-connect/auth/device"

    # oidc token endpoint
    oidc_token_endpoint = base_url + "protocol/openid-connect/token"

    print("Initiating device auth flow to setup offline access token.")
    print()
    device_auth_response = initiate_device_auth_flow(
        client_id=client_id,
        device_endpoint=oidc_device_auth_endpoint,
        scopes=scopes
    )

    print("Decoding response")
    print()
    device_code = device_auth_response['device_code']
    user_code = device_auth_response['user_code']
    verification_uri = device_auth_response['verification_uri_complete']
    interval = device_auth_response['interval']

    print("Please authorise using the following endpoint.")
    print()
    display_device_auth_flow(user_code, verification_uri)
    print()

    print("Awaiting completion")
    print()
    oauth_tokens = await_device_auth_flow_completion(
        device_code=device_code,
        client_id=client_id,
        interval=interval,
        grant_type=device_grant_type,
        scopes=scopes,
        token_endpoint=oidc_token_endpoint
    )
    print()

    if oauth_tokens is None:
        raise Exception(
            "Failed to retrieve tokens from device authorisation flow!")
        
    if export_to_env:
        print("Establishing environment variable.")
        os.environ['RRAP_OFFLINE_TOKEN'] = oauth_tokens['refresh_token']

    return oauth_tokens['refresh_token']
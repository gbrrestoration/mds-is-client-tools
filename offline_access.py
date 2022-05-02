import requests
from typing import Any, Dict, List
import os

"""
Defines a function which allows exchange of environment variable
RRAP_OFFLINE_TOKEN for a fresh access token.
"""

def perform_offline_refresh(refresh_token: str, client_id: str, scopes: List[str], token_endpoint: str) -> Dict[str, Any]:  
    """    perform_offline_refresh
        Exchanges a refresh token for an access token with the specified client id, 
        scopes and endpoint. Used to exchange offline token for access token.

        Arguments
        ----------
        refresh_token : str
            The offline or regular refresh token
        client_id : str
            The client id 
        scopes : List[str]
            The oidc scopes required (e.g. ["roles"])
        token_endpoint : str
            The endpoint to send request to

        Returns
        -------
         : Dict[str, Any]
            JSON response from API endpoint which includes ['access_token'] field

        See Also (optional)
        --------
        https://developer.okta.com/docs/reference/api/oidc/#token

        Examples (optional)
        --------
    """

    # Perform a refresh grant
    refresh_grant_type = "refresh_token"

    # Required openid connect fields
    data = {
        "grant_type": refresh_grant_type,
        "client_id": client_id,
        "refresh_token": refresh_token,
        "scope": " ".join(scopes)
    }
    
    # Send API request 
    response = requests.post(token_endpoint, data=data)
    
    if (not response.status_code == 200):
        raise Exception(f"Something went wrong during token refresh. Status code: {response.status_code}.")
    
    return response.json()


def exchange_offline_for_access(client_id : str = "automated-access", scopes: List[str] = ["roles"]) -> str:
    """    exchange_offline_for_access
        Exchanges offline token for access token using the refresh token flow.
        
        Expects RRAP_OFFLINE_TOKEN environment variable to be set to the offline refresh token.

        Arguments
        ----------
        client_id : str, optional
            The client id, default = "automated-access"
        scopes : List[str], optional
            The openid connect scopes desired, default = ["roles"]

        Returns
        -------
         : str
            The access token

        Raises
        ------
        Exception
            If RRAP_OFFLINE_TOKEN environment variable is not present.

        See Also (optional)
        --------

        Examples (optional)
        --------
    """
    # Base auth URL
    base_url = "https://auth.rrap-is.com/auth/realms/rrap/"

    # oidc token endpoint
    oidc_token_endpoint = base_url + "protocol/openid-connect/token"

    # get offline token from environment
    OFFLINE_TOKEN = os.getenv("RRAP_OFFLINE_TOKEN", None)

    if (OFFLINE_TOKEN == None):
        raise Exception(
            "No offline token detected, expecting RRAP_OFFLINE_TOKEN environment variable.")

    print("Refreshing using offline access token")
    print()

    refreshed = perform_offline_refresh(
        refresh_token=OFFLINE_TOKEN,
        client_id=client_id,
        scopes=scopes,
        token_endpoint=oidc_token_endpoint
    )
    
    # unpack response and return access token
    return refreshed['access_token']


if __name__ == '__main__':
    token = exchange_offline_for_access()
    print(f"Retrieved access token:\n{token}")

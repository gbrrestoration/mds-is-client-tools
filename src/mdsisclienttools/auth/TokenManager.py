import webbrowser
import requests
import time
from jose import jwt  # type: ignore
from jose.constants import ALGORITHMS  # type: ignore
from pydantic import BaseModel
from enum import Enum
from typing import Dict, Optional, List, Any

# For usage in requests library
class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token: str):
        self.token = token

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        r.headers["authorization"] = "Bearer " + self.token
        return r


# Model for storing and serialising tokens
class Stage(str, Enum):
    TEST = "TEST"
    DEV = "DEV"
    STAGE = "STAGE"
    PROD = "PROD"


class Tokens(BaseModel):
    access_token: str
    refresh_token: str


class StageTokens(BaseModel):
    stages: Dict[Stage, Optional[Tokens]]


LOCAL_STORAGE_DEFAULT = ".tokens.json"
DEFAULT_CLIENT_ID = "client-tools"

class DeviceFlowManager:
    def __init__(
        self,
        stage: str,
        keycloak_endpoint: str,
        client_id: str = DEFAULT_CLIENT_ID,
        local_storage_location: str = LOCAL_STORAGE_DEFAULT,
        scopes: List[str] = [],
        force_token_refresh: bool = False,
        silent : bool = False
    ) -> None:
        """Generates a manager class. This manager class uses the 
        OAuth device authorisation flow to generate credentials 
        on a per application stage basis. The tokens are automatically
        refreshed when accessed through the get_auth() function. 
        
        Tokens are cached in local storage with a configurable file
        name and are only reproduced if the refresh token expires.

        Parameters
        ----------
        stage : str
            The application stage to use. Choose from {list(Stage)}.
        keycloak_endpoint : str
            The keycloak endpoint to use.
        client_id : str, optional
            The client id for the keycloak authorisation, by default DEFAULT_CLIENT_ID
        local_storage_location : str, optional
            The storage location for caching creds, by default LOCAL_STORAGE_DEFAULT
        scopes : List[str], optional
            The scopes you want to request against client, by default []
        force_token_refresh : bool, optional
            If you want to force the manager to dump current creds, by default False
        silent : bool
            Force silence in the stdout outputs for use in context where printing
            would be irritating. By default False (helpful messages are printed).

        Raises
        ------
        ValueError
            If the stage provided is invalid.
        """
        self.keycloak_endpoint = keycloak_endpoint
        self.client_id = client_id
        self.silent = silent

        # initialise empty stage tokens
        self.stage_tokens: Optional[Tokens] = None
        self.public_key: Optional[str] = None
        self.scopes: List[str] = scopes

        # pull out stage
        try:
            self.stage: Stage = Stage[stage]
        except:
            raise ValueError(f"Stage {stage} is not one of {list(Stage)}.")

        # set endpoints
        self.token_endpoint = self.keycloak_endpoint + "/protocol/openid-connect/token"
        self.device_endpoint = self.keycloak_endpoint + \
            "/protocol/openid-connect/auth/device"
        self.token_storage_location = local_storage_location

        if force_token_refresh:
            self.reset_local_storage()

        self.retrieve_keycloak_public_key()
        self.get_tokens()
    
    def optional_print(self, message:str) -> None:
        """Prints only if the silent value is not 
        flagged.

        Parameters
        ----------
        message : str
            The message to print.
        """
        if not self.silent:
            print(message)

    def retrieve_local_tokens(self, stage: Stage) -> Optional[Tokens]:
        """Retrieves credentials from a local cache file, if present. 
        Credentials are on a per stage basis. If the creds are valid
        but expired, they will be refreshed. If this fails, then 
        a failure is indicated by None. 

        Parameters
        ----------
        stage : Stage
            The stage to fetch creds for.

        Returns
        -------
        Optional[Tokens]
            Tokens object if successful or None.
        """
        print("Looking for existing tokens in local storage.")
        print()
        # Try to read file
        try:
            stage_tokens = StageTokens.parse_file(self.token_storage_location)
            tokens = stage_tokens.stages.get(stage)
            assert tokens
        except:
            print(f"No local storage tokens for stage {stage} found.")
            print()
            return None

        # Validate
        print("Validating found tokens")
        print()
        valid = True
        try:
            self.validate_token(tokens=tokens)
        except:
            valid = False

        # Return the tokens found if valid
        if valid:
            print("Found tokens valid, using.")
            print()
            return tokens

        # Tokens found but were invalid, try refreshing
        refresh_succeeded = True
        try:
            print("Trying to use found tokens to refresh the access token.")
            print()
            refreshed = self.perform_refresh(tokens=tokens)

            # unpack response and return access token
            access_token = refreshed.get('access_token')
            refresh_token = refreshed.get('refresh_token')

            # Make sure they are preset
            assert access_token
            assert refresh_token

            tokens = Tokens(
                access_token=access_token,
                refresh_token=refresh_token
            )
            self.validate_token(tokens)
        except:
            refresh_succeeded = False

        # If refresh fails for some reason then return None
        # otherwise return the tokens
        if refresh_succeeded:
            print("Token refresh successful.")
            print()
            return tokens
        else:
            print("Tokens found in storage but they are not valid.")
            print()
            return None

    def reset_local_storage(self) -> None:
        """Resets the local storage by setting all 
        values to None.
        """
        print("Flushing tokens from local storage.")
        cleared_tokens = StageTokens(
            stages={
                Stage.TEST: None,
                Stage.DEV: None,
                Stage.STAGE: None,
                Stage.PROD: None
            }
        )

        # Dump the cleared file into storage
        with open(self.token_storage_location, 'w') as f:
            f.write(cleared_tokens.json())

    def update_local_storage(self, stage: Stage) -> None:
        """Pulls the current StageTokens object from cache
        storage, if present, then either updates the current
        stage token value in existing or new StageTokens 
        object. Writes back to file.

        Parameters
        ----------
        stage : Stage
            The stage to update
        """
        # Check current tokens
        assert self.tokens
        existing: Optional[bool] = None
        existing_tokens: Optional[StageTokens] = None
        try:
            existing_tokens = StageTokens.parse_file(
                self.token_storage_location)
            existing = True
        except:
            existing = False

        assert existing is not None
        if existing:
            # We have existing - update current stage
            assert existing_tokens

            existing_tokens.stages[stage] = self.tokens
        else:
            existing_tokens = StageTokens(
                stages={
                    Stage.TEST: None,
                    Stage.DEV: None,
                    Stage.STAGE: None,
                    Stage.PROD: None
                }
            )
            existing_tokens.stages[stage] = self.tokens

        # Dump the file into storage
        with open(self.token_storage_location, 'w') as f:
            f.write(existing_tokens.json())

    def get_tokens(self) -> None:
        """Tries to get tokens. 
        First attempts to pull from the local storage. 
        Otherwise initiates a device auth flow then uses the 
        token endpoint to generate the creds.

        Raises
        ------
        Exception
            OAuth tokens not present in device auth flow
        Exception
            Tokens not present in keycloak token endpoint response
        """
        # Try getting from local storage first
        # These are always validated
        print("Attempting to generate authorisation tokens.")
        print()

        retrieved_tokens = self.retrieve_local_tokens(self.stage)
        if retrieved_tokens:
            self.tokens = retrieved_tokens
            self.update_local_storage(self.stage)
            return

        # Otherwise do a normal authorisation flow
        # grant type
        device_grant_type = "urn:ietf:params:oauth:grant-type:device_code"

        print("Initiating device auth flow to setup offline access token.")
        print()
        device_auth_response = self.initiate_device_auth_flow()

        print("Decoding response")
        print()
        device_code = device_auth_response['device_code']
        user_code = device_auth_response['user_code']
        verification_uri = device_auth_response['verification_uri_complete']
        interval = device_auth_response['interval']

        print("Please authorise using the following endpoint.")
        print()
        self.display_device_auth_flow(user_code, verification_uri)
        print()

        print("Awaiting completion")
        print()
        oauth_tokens = self.await_device_auth_flow_completion(
            device_code=device_code,
            interval=interval,
            grant_type=device_grant_type,
        )
        print()

        if oauth_tokens is None:
            raise Exception(
                "Failed to retrieve tokens from device authorisation flow!")

        # pull out the refresh and access token
        # this refresh token is standard (not offline access)
        access_token = oauth_tokens.get('access_token')
        refresh_token = oauth_tokens.get('refresh_token')

        # Check that they are present
        try:
            assert access_token is not None
            assert refresh_token is not None
        except Exception as e:
            raise Exception(
                f"Token payload did not include access or refresh token: Error: {e}")
        # Set tokens
        self.tokens = Tokens(
            access_token=access_token,
            refresh_token=refresh_token
        )
        self.update_local_storage(self.stage)

        print("Token generation complete. Authorisation successful.")
        print()

    def perform_token_refresh(self) -> None:
        """Updates the current tokens by using the refresh token.
        """
        assert self.tokens is not None

        print("Refreshing using refresh token")
        print()

        refreshed = self.perform_refresh()

        # unpack response and return access token
        access_token = refreshed.get('access_token')
        refresh_token = refreshed.get('refresh_token')

        # Make sure they are preset
        assert access_token
        assert refresh_token

        self.tokens = Tokens(
            access_token=access_token,
            refresh_token=refresh_token
        )
        self.update_local_storage(self.stage)

    def perform_refresh(self, tokens: Optional[Tokens] = None) -> Dict[str, Any]:
        """Helper function to perform refresh. This accepts tokens 
        and other information from the class, calls the refresh endpoint, 
        and responds with the keycloak token endpoint response.

        Parameters
        ----------
        tokens : Optional[Tokens], optional
            The tokens object, by default None

        Returns
        -------
        Dict[str, Any]
            The response from the keycloak endpoint as json dict.

        Raises
        ------
        Exception
            Non 200 response code.
        """
        # Perform a refresh grant
        refresh_grant_type = "refresh_token"

        # make sure we have tokens to use
        desired_tokens: Optional[Tokens]
        if tokens:
            desired_tokens = tokens
        else:
            desired_tokens = self.tokens

        assert desired_tokens

        # Required openid connect fields
        data = {
            "grant_type": refresh_grant_type,
            "client_id": self.client_id,
            "refresh_token": desired_tokens.refresh_token,
            "scope": " ".join(self.scopes)
        }

        # Send API request
        response = requests.post(self.token_endpoint, data=data)

        if (not response.status_code == 200):
            raise Exception(
                f"Something went wrong during token refresh. Status code: {response.status_code}.")

        return response.json()

    def initiate_device_auth_flow(self) -> Dict[str, Any]:
        """Initiates OAuth device flow. 
        This is triggered by a post request to the device endpoint
        of the keycloak server. The specified client (by id) must be 
        public and have the device auth flow enabled.

        Returns
        -------
        Dict[str, Any]
            The json response info from the device auth flow endpoint
        """ 
        data = {
            "client_id": self.client_id,
            "scope": ' '.join(self.scopes)
        }
        response = requests.post(self.device_endpoint, data=data).json()
        return response

    def get_auth(self) -> BearerAuth:
        """A helper function which produces a BearerAuth object for use
        in the requests.xxx objects. For example: 
        
        manager = DeviceAuthFlowManager(...)
        auth = manager.get_auth 
        requests.post(..., auth=auth)

        Returns
        -------
        BearerAuth
            The requests auth object.

        Raises
        ------
        Exception
            Tokens are not present
        Exception
            Token validation failed and refresh or device auth failed
        """
        # make auth object using access_token
        if (self.tokens is None or self.public_key is None):
            raise Exception(
                "cannot generate bearer auth object without access token or public key")

        assert self.tokens
        assert self.public_key
        
        # are tokens valid?
        try:
            self.validate_token()
        except Exception as e:
            # tokens are invalid
            print(f"Token validation failed due to error: {e}")
            # does token refresh work?
            try:
                self.perform_token_refresh()
                self.validate_token()
            except Exception as e:
                try:
                    # Does new token generation work?
                    self.get_tokens()
                    self.validate_token()
                except Exception as e:
                    raise Exception(
                        f"Device log in failed, access token expired/invalid, and refresh failed. Error: {e}")
        return BearerAuth(token=self.tokens.access_token)

    def retrieve_keycloak_public_key(self) -> None:
        """Given the keycloak endpoint, retrieves the advertised
        public key.
        Based on https://github.com/nurgasemetey/fastapi-keycloak-oidc/blob/main/main.py
        """
        error_message = f"Error finding public key from keycloak endpoint {self.keycloak_endpoint}."
        try:
            r = requests.get(self.keycloak_endpoint,
                       timeout=3)
            r.raise_for_status()
            response_json = r.json()
            self.public_key = f"-----BEGIN PUBLIC KEY-----\r\n{response_json['public_key']}\r\n-----END PUBLIC KEY-----"
        except requests.exceptions.HTTPError as errh:
            print(error_message)
            print("Http Error:", errh)
            raise errh
        except requests.exceptions.ConnectionError as errc:
            print(error_message)
            print("Error Connecting:", errc)
            raise errc
        except requests.exceptions.Timeout as errt:
            print(error_message)
            print("Timeout Error:", errt)
            raise errt
        except requests.exceptions.RequestException as err:
            print(error_message)
            print("An unknown error occured:", err)
            raise err

    def display_device_auth_flow(self, user_code: str, verification_url: str) -> None:
        """Displays the current device auth flow challenge - first by trying to 
        open a browser window - if this fails then prints suggestion to stdout 
        to try using the URL manually.

        Parameters
        ----------
        user_code : str
            The user code
        verification_url : str
            The url which embeds challenge code
        """
        print(f"Verification URL: {verification_url}")
        print(f"User Code: {user_code}")
        try:
            webbrowser.open(verification_url)
        except Exception:
            print("Tried to open web-browser but failed. Please visit URL above.")

    def await_device_auth_flow_completion(
        self,
        device_code: str,
        interval: int,
        grant_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Ping the token endpoint as specified in the OAuth standard
        at the advertised polling rate until response is positive
        or failure.

        Parameters
        ----------
        device_code : str
            The device code
        interval : int
            The polling interval (ms)
        grant_type : str
            The OAuth grant type

        Returns
        -------
        Optional[Dict[str, Any]]
            If successful, the keycloak response
        """
        # set up request
        data = {
            "grant_type": grant_type,
            "device_code": device_code,
            "client_id": self.client_id,
            "scope": " ".join(self.scopes)
        }

        # Setup success criteria
        succeeded = False
        timed_out = False
        misc_fail = False

        # start time
        response_data: Optional[Dict[str, Any]] = None

        # get requests session for repeated queries
        session = requests.session()

        # Poll for success
        while not succeeded and not timed_out and not misc_fail:
            response = session.post(self.token_endpoint, data=data)
            response_data = response.json()
            assert response_data
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
            assert response_data
            print(f"Failed due to {response_data['error']}")
            return None
        except Exception as e:
            print(
                f"Failed with unknown error, failed to find error message. Error {e}")
            return None

    def validate_token(self, tokens: Optional[Tokens] = None) -> None:
        """Uses the python-jose library to validate current creds.
        
        In this context, it is basically just checking signature
        and expiry. The tokens are enforced at the API side 
        as well.

        Parameters
        ----------
        tokens : Optional[Tokens], optional
            The tokens object to validate, by default None
        """
        # Validate either self.tokens or supply tokens optionally
        test_tokens: Optional[Tokens]
        if tokens:
            test_tokens = tokens
        else:
            test_tokens = self.tokens

        # Check tokens are present
        assert test_tokens
        assert self.public_key

        # this is currently locally validating the token
        # It is our responsibility to choose whether to honour the expiration date
        # etc
        # this will throw an exception if invalid
        jwt_payload = jwt.decode(
            test_tokens.access_token,
            self.public_key,
            algorithms=[ALGORITHMS.RS256],
            options={
                "verify_signature": True,
                "verify_aud": False,
                "exp": True
            }
        )

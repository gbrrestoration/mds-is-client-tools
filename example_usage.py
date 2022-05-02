from get_offline_code import generate_offline_access_token
from offline_access import exchange_offline_for_access
import os
import requests

# Basic bearer auth scheme as per 
# https://stackoverflow.com/questions/29931671/making-an-api-call-in-python-with-an-api-that-requires-a-bearer-token
class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


if __name__ == "__main__":
    offline_token = os.getenv('RRAP_OFFLINE_TOKEN')
    if offline_token:
        print("Detected existing offline token environment variable. Not generating another one.")
    else:
        print("No offline token detected - if you have an existing token you should include it as RRAP_OFFLINE_TOKEN environment variable.")

        answered = False
        while not answered:
            yes_or_no = input(
                "Do you want to generate a token now? This will require access to a phone or browser; 'y' or 'n'?\n")
            if yes_or_no.upper() not in ['YES', 'Y', 'NO', 'N']:
                print("Invalid response.")
            else:
                answered = True
        response = yes_or_no.upper() in ['YES', 'Y']

        if response:
            print("Generating offline token now.")
            answered = False
            while not answered:
                yes_or_no = input(
                    "Do you want to automatically export the variable to your environment? If you do not, the program will exit after generating token so that you can store it and include the environment variable. Include, 'y' or 'n'?\n")
                if yes_or_no.upper() not in ['YES', 'Y', 'NO', 'N']:
                    print("Invalid response.")
                else:
                    answered = True
            response = yes_or_no.upper() in ['YES', 'Y']

            offline_token = generate_offline_access_token(
                export_to_env=response)
            print("Your offline token is:")
            print(offline_token)
            print(
                "Please store this securely and include as RRAP_OFFLINE_TOKEN in the future.")

            if response:
                input("Please press enter once you have saved this token securely.")
                print("Proceeding to generate access token.")
            else:
                print("Exiting program.")
                exit(0)
        else:
            print(
                "Please include your existing offline token as an environment variable RRAP_OFFLINE_TOKEN.")
            print("Exiting program.")
            exit(0)

    # Get access token
    print("Generating access token.")
    access_token = exchange_offline_for_access(
        client_id="test-programmatic-client", scopes=["roles"])
    
    # Show access token 
    print("Generated access token:")
    print(access_token)

    # Make API request
    print("Making sample authenticated API request.")
    endpoint = "https://data-api.dev.rrap-is.com/check-access/check-general-access"
    response = requests.get(endpoint, auth=BearerAuth(token=access_token))
    
    # Parse response status 
    if (response.status_code == 200):
        print("API request successful.")
    else:
        print(f"API request failed, status code: {response.status_code}.")

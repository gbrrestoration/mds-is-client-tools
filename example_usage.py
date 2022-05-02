from get_offline_code import generate_offline_access_token
from offline_access import exchange_offline_for_access
import os
import requests
from typing import Dict, Any

# Basic bearer auth scheme as per
# https://stackoverflow.com/questions/29931671/making-an-api-call-in-python-with-an-api-that-requires-a-bearer-token


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


def fetch_datasets(auth: BearerAuth):
    endpoint = "https://data-api.rrap-is.com/registry/items/list-all-datasets"
    response = requests.get(endpoint, auth=auth)

    # Check successful
    assert response.status_code == 200
    response = response.json()
    assert response['status']['success']

    # Check at least one item
    assert response['num_items'] > 0

    # Return the items
    return response['registry_items']


def read_dataset(s3_info: Dict[str, Any], auth: BearerAuth):
    endpoint = "https://data-api.rrap-is.com/registry/credentials/generate-read-access-credentials"
    response = requests.post(endpoint, json=s3_info, auth=auth)
    

    # Check successful
    assert response.status_code == 200
    response = response.json()
    assert response['status']['success']

    # Give back AWS creds
    return response['credentials']

def print_creds(creds : Dict[str, Any]):
    transform = lambda name, val : f"export {name.upper()}=\"{val}\""
    item_list = []
    for key,val in creds.items():
        if (key!="expiry"):
            item_list.append(transform(key,val))
    print('\n'.join(item_list))

def print_command_suggestion(s3_loc : Dict[str,Any]):
    print(f"To view: aws s3 ls {s3_loc['s3_uri']}\nTo download (into folder 'data'): aws s3 sync {s3_loc['s3_uri']} data/")

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
    client_id = "automated-access"
    scopes = ["roles"]
    print("Generating access token.")
    access_token = exchange_offline_for_access(
        client_id=client_id, scopes=scopes)

    # Show access token
    print("Generated access token:")
    print(access_token)

    # Pull out auth object
    auth = BearerAuth(token=access_token)

    # Get datasets
    dataset_list = fetch_datasets(auth=auth)

    # Get the first item
    first_item = dataset_list[0]

    # get s3 location and handle info
    handle = first_item['handle']
    s3_loc = first_item['s3']

    # get read credentials for this dataset
    creds = read_dataset(s3_loc, auth=auth)
    
    # print to terminal
    print()
    print("Access information for:")
    print(s3_loc)
    print()
    print_creds(creds)
    print()
    print("Command suggestions:")
    print_command_suggestion(s3_loc)
    
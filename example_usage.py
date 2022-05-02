from get_offline_code import generate_offline_access_token
from offline_access import exchange_offline_for_access
import os
import requests
from typing import Dict, Any, Optional, List
import cloudpathlib.s3 as s3


# Basic bearer auth scheme as per
# https://stackoverflow.com/questions/29931671/making-an-api-call-in-python-with-an-api-that-requires-a-bearer-token


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


def fetch_datasets(auth: BearerAuth) -> List[Dict[str, Any]]:
    """    fetch_datasets
        Given basic bearer auth will call the fetch 
        datasets API endpoint to find an example dataset. 

        Arguments
        ----------
        auth : BearerAuth
            The bearer auth object 

        Returns
        -------
         : List[Dict[str,Any]]
            The list of registry items

        See Also (optional)
        --------

        Examples (optional)
        --------
    """
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


def fetch_dataset(handle_id: str, auth: BearerAuth) -> Optional[Dict[str, Any]]:
    """    fetch_dataset
        Given the handle ID to lookup and the basic auth will 
        call the fetch dataset data store API to get more 
        information about the dataset.

        Arguments
        ----------
        handle_id : str
            The handle ID to lookup
        auth : BearerAuth
            The bearer token auth

        Returns
        -------
         : Optional[Dict[str, Any]]
            A dictionary for the item if found or None if not

        Raises
        ------
        Exception
            If a non status code 200 response.

        See Also (optional)
        --------

        Examples (optional)
        --------
    """
    endpoint = "https://data-api.rrap-is.com/registry/items/fetch-dataset"
    params = {
        'handle_id': handle_id
    }
    response = requests.get(endpoint, params=params, auth=auth)

    # Check successful
    try:
        assert response.status_code == 200
        assert response.json()['status']['success']

        # Return the items
        return response.json()['registry_item']
    except Exception as e:
        if (response.status_code == 200):
            return None
        else:
            raise e


def read_dataset(s3_info: Dict[str, Any], auth: BearerAuth) -> Dict[str, Any]:
    """    read_dataset
        Gets AWS read credentials using the data store API.

        Arguments
        ----------
        s3_info : Dict[str, Any]
            the s3 location of the object
        auth : BearerAuth
            The bearer token auth

        Returns
        -------
         : Dict[str,Any]
            AWS credentials

        See Also (optional)
        --------

        Examples (optional)
        --------
    """
    endpoint = "https://data-api.rrap-is.com/registry/credentials/generate-read-access-credentials"
    response = requests.post(endpoint, json=s3_info, auth=auth)

    # Check successful
    assert response.status_code == 200
    response = response.json()
    assert response['status']['success']

    # Give back AWS creds
    return response['credentials']


def print_creds(creds: Dict[str, Any]) -> None:
    """    print_creds
        Given the creds objects, displays an AWS export
        format.

        Arguments
        ----------
        creds : Dict[str, Any]
            The AWS creds

        See Also (optional)
        --------

        Examples (optional)
        --------
    """
    def transform(name, val): return f"export {name.upper()}=\"{val}\""
    item_list = []
    for key, val in creds.items():
        if (key != "expiry"):
            item_list.append(transform(key, val))
    print('\n'.join(item_list))


def print_command_suggestion(s3_loc: Dict[str, Any]) -> None:
    """    print_command_suggestion
        Prints a suggestion of some basic S3 commands.

        Arguments
        ----------
        s3_loc : Dict[str, Any]
            The s3 location object

        See Also (optional)
        --------

        Examples (optional)
        --------
    """
    print(
        f"To view: aws s3 ls {s3_loc['s3_uri']}\nTo download (into folder 'data'): aws s3 sync {s3_loc['s3_uri']} data/")


def download_files(s3_loc: Dict[str, str], s3_creds: Dict[str, Any], destination_dir: str) -> None:
    """    download_files
        Uses the cloudpathlib library to download all the files and sub dirs/files from 
        the specified s3 location (s3_uri in s3_loc) into the specified destination 
        directory.

        Arguments
        ----------
        s3_loc : Dict[str, str]
            S3 location object
        s3_creds : Dict[str, Any]
            S3 creds which match input format (i.e. expiry attribute dropped)
        destination_dir : str
            The relative destination directory - will be created if required

        See Also (optional)
        --------

        Examples (optional)
        --------
    """
    # create client
    client = s3.S3Client(
        **s3_creds
    )
    # create path
    path = s3.S3Path(cloud_path=s3_loc['s3_uri'], client=client)
    # download
    path.download_to(destination_dir)


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

    existing_handle = False
    responded = False
    while not responded:
        existing_handle_input = input(
            "Do you have an existing handle to download? y or n\n")
        existing_handle_input = existing_handle_input.upper().strip()
        if existing_handle_input in ['YES', 'Y', 'N', 'NO']:
            responded = True
            existing_handle = existing_handle_input in ['YES', 'Y']
        else:
            print("Invalid input... y or n")

    if existing_handle:
        responded = False
        while not responded:
            handle_input = input(
                "What is the handle? Please enter it below and press enter to confirm:\n")
            handle_input = handle_input.upper().strip()

            # Get info about handle
            response = fetch_dataset(handle_id=handle_input, auth=auth)

            # Handle was found
            if response:
                responded = True
                s3_loc = response['s3']
                handle = handle_input

                print(f"Found dataset: {response['dataset_name']}.")
            else:
                # Handle was not found
                print(
                    "Invalid input... the dataset with that handle could not be found.")

    else:
        print("Getting first entry in registry since no handle was supplied.")

        # Get datasets
        dataset_list = fetch_datasets(auth=auth)

        # Get the first item
        first_item = dataset_list[0]
        print(f"Found dataset: {first_item['dataset_name']}.")

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

    print()
    print("Attempting to download files to test_directory")

    # Don't need expiry to use
    del creds['expiry']
    download_files(s3_loc=s3_loc, s3_creds=creds,
                   destination_dir="test_directory")
    print(f"Download complete.")

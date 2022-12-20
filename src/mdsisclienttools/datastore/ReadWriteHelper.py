import requests
from typing import Dict, Any, Optional, List
import cloudpathlib.s3 as s3  # type: ignore
from mdsisclienttools.auth.TokenManager import BearerAuth


DEFAULT_DATA_STORE_ENDPOINT = "https://data-api.mds.gbrrestoration.org"


def _fetch_all_datasets(auth: BearerAuth, endpoint: str = DEFAULT_DATA_STORE_ENDPOINT) -> List[Dict[str, Any]]:
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
    _endpoint = endpoint + "/registry/items/list-all-datasets"
    response = requests.get(_endpoint, auth=auth)

    # Check successful
    assert response.status_code == 200
    response = response.json()
    assert response['status']['success']

    # Return the items
    return response['registry_items']


def _fetch_dataset(handle_id: str, auth: BearerAuth, endpoint: str = DEFAULT_DATA_STORE_ENDPOINT) -> Optional[Dict[str, Any]]:
    """ _fetch_dataset
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
    fetch_endpoint = endpoint + "/registry/items/fetch-dataset"
    params = {
        'handle_id': handle_id
    }
    response = requests.get(fetch_endpoint, params=params, auth=auth)

    # Check successful
    try:
        assert response.status_code == 200
        assert response.json()['status']['success']

        # Return the items
        return response.json()['item']
    except Exception as e:
        if (response.status_code == 200):
            return None
        else:
            raise e


def _read_dataset(dataset_id: str, auth: BearerAuth, endpoint: str = DEFAULT_DATA_STORE_ENDPOINT) -> Dict[str, Any]:
    """    read_dataset
        Gets AWS read credentials using the data store API.

        Arguments
        ----------
        dataset_id : Dict[str, Any]
            The datasets handle ID
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
    read_cred_endpoint = endpoint + \
        "/registry/credentials/generate-read-access-credentials"
    response = requests.post(read_cred_endpoint, json={
        "dataset_id": dataset_id,
        "console_session_required": False
    }, auth=auth)

    # Check successful
    assert response.status_code == 200
    response = response.json()
    assert response['status']['success']

    # Give back AWS creds
    return response['credentials']


def _write_dataset(dataset_id: str, auth: BearerAuth, endpoint: str = DEFAULT_DATA_STORE_ENDPOINT) -> Dict[str, Any]:
    """  _write_dataset
        Gets AWS write credentials using the data store API.

        Arguments
        ----------
        dataset_id : Dict[str, Any]
            The datasets handle ID
        auth : BearerAuth
            The bearer token auth

        See Also (optional)
        --------

        Examples (optional)
        --------
    """
    write_credential_endpoint = endpoint + \
        "/registry/credentials/generate-write-access-credentials"
    response = requests.post(write_credential_endpoint,
                             json={
                                 "dataset_id": dataset_id,
                                 "console_session_required": False
                             }, auth=auth)

    # Check successful
    assert response.status_code == 200, f"Expected response 200OK but got {response.status_code}"
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
    def transform(
        name: str, val: str) -> str: return f"export {name.upper()}=\"{val}\""
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


def _download_files(s3_loc: Dict[str, str], s3_creds: Dict[str, Any], destination_dir: str) -> None:
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
    #Release file handles
    path.__del__


def _upload_files(s3_loc: Dict[str, str], s3_creds: Dict[str, Any], source_dir: str) -> None:
    # create client
    client = s3.S3Client(**s3_creds)
    # create path
    path = s3.S3Path(cloud_path=s3_loc['s3_uri'], client=client)
    # download
    path.upload_from(source_dir)
    #Release file handles
    path.__del__


def upload(handle: str, auth: BearerAuth, source_dir: str, data_store_api_endpoint: str = DEFAULT_DATA_STORE_ENDPOINT) -> None:
    """Given a source path, handle and authorisation information, will
    retrieve read only credentials from the data store API, fetch the 
    dataset information, then upload all the dataset files to the 
    handle id specified location. 

    Parameters
    ----------
    handle : str
        The handle ID of the dataset to download.
    auth : BearerAuth
        The bearer auth object. See TokenManager library.
    source_dir : str
        The path of to folder of files to upload.

    Raises
    ------
    ValueError
        Raises a value error if the handle id is invalid.
    """
    # Get info about handle
    response = _fetch_dataset(
        handle_id=handle, auth=auth, endpoint=data_store_api_endpoint)

    # Handle was found
    if response:
        s3_loc = response['s3']

        print(
            f"Found dataset: {response['collection_format']['dataset_info']['name']}.")
    else:
        # Handle was not found
        raise ValueError(
            f'Invalid input... the dataset with that handle: {handle} could not be found.')

    # get write credentials for this dataset
    creds = _write_dataset(handle, auth=auth, endpoint=data_store_api_endpoint)

    print()
    print(f'Attempting to upload files to {source_dir}')

    # Don't need expiry to use
    del creds['expiry']
    _upload_files(s3_loc=s3_loc, s3_creds=creds,
                  source_dir=source_dir)
    print(f"Upload complete.")


def download(download_path: str, handle: str, auth: BearerAuth, data_store_api_endpoint: str = DEFAULT_DATA_STORE_ENDPOINT) -> None:
    """Given a download path, handle and authorisation information, will
    retrieve read only credentials from the data store API, fetch the 
    dataset information, then download all the dataset files to the 
    specified location. 

    Parameters
    ----------
    download_path : str
        The path of to download the files to. If the folder/path does not
        exist, this will create the folder. If there are nested folders, 
        all folders/files will be downloaded and paths created.
    handle : str
        The handle ID of the dataset to download.
    auth : BearerAuth
        The bearer auth object. See TokenManager library.

    Raises
    ------
    ValueError
        Raises a value error if the dataset cannot be found.
    """
    # Get info about handle
    response = _fetch_dataset(
        handle_id=handle, auth=auth, endpoint=data_store_api_endpoint)

    # Handle was found
    if response:
        s3_loc = response['s3']

        print(
            f"Found dataset: {response['collection_format']['dataset_info']['name']}.")
    else:
        # Handle was not found
        raise ValueError(
            f'Invalid input... the dataset with that handle: {handle} could not be found.')

    # get read credentials for this dataset
    creds = _read_dataset(handle, auth=auth, endpoint=data_store_api_endpoint)

    print()
    print(f'Attempting to download files to {download_path}')

    # Don't need expiry to use
    del creds['expiry']
    _download_files(s3_loc=s3_loc, s3_creds=creds,
                    destination_dir=download_path)
    print(f"Download complete.")

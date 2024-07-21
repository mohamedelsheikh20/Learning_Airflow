from include.helpers.minio import get_minio_client
from airflow.hooks.base import BaseHook
from io import BytesIO
import requests
import json


# Function to get prices from API (used in task)
def _get_stock_prices(url, symbol):
    # get the url of certain company (SYMBOL='AAPL' in our case)
    url = f"{url}{symbol}?metrics=high?&interval=1d&range=1y"

    # get the connection from the Airflow UI
    api = BaseHook.get_connection('stock_api')

    # get the certain link using all data we get
    response = requests.get(url, headers=api.extra_dejson['headers'])

    # return what we just need and convert it from dict to JSON
    return json.dumps(response.json()['chart']['result'][0])



# Function to store prices (used in task)
def _store_prices(prices):
    # Convert the JSON string `prices` to a Python dictionary
    prices = json.loads(prices)

    # helper funcions that used many times in seperate file 
    client = get_minio_client()

    ## we can print to check data into the log in the docker
    # print(client)

    # Define the bucket name where the data will be stored
    bucket_name = 'stock-market'

    # Check if the bucket exists in MinIO, if not, create it
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
    
    # Extract the stock symbol from the prices dictionary
    symbol = prices['meta']['symbol']

    # Convert the `prices` dictionary back to a JSON string and encode it to bytes
    data = json.dumps(prices, ensure_ascii=False).encode('utf8')

    # Store the JSON data in MinIO under the specified bucket and object name
    objw = client.put_object(
        bucket_name=bucket_name,  # Name of the bucket to store the object
        object_name=f'{symbol}/prices.json',  # Path and name of the object in the bucket
        data=BytesIO(data),  # Data to be stored (as a byte stream)
        length=len(data)  # Length of the data to be stored
    )

    # Return the path of the stored object in the format "bucket_name/symbol" = "stock-market/AAPL"
    return f'{objw.bucket_name}/{symbol}'
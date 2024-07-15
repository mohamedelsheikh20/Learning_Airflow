from airflow.hooks.base import BaseHook
import requests
import json


def _get_stock_prices(url, symbol):
    # get the url of certain company (SYMBOL='AAPL' in our case)
    url = f"{url}{symbol}?metrics=high?&interval=1d&range=1y"

    # get the connection from the Airflow UI
    api = BaseHook.get_connection('stock_api')

    # get the certain link using all data we get
    response = requests.get(url, headers=api.extra_dejson['headers'])

    # return what we just need and convert it from dict to JSON
    return json.dumps(response.json()['chart']['result'][0])
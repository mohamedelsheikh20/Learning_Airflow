# -------------------------------------- this is one DAG -------------------------------------- #

# Imports
# ---------------------------------------------------------------------------------------------- #

# Create DAGs and tasks using decorators (faster and lighter)
from airflow.decorators import dag, task

# To link the APIs on the UI website to the code here
# Class provides methods to interact with external services or tools (Postgres / Snowflake / etc.)
from airflow.hooks.base import BaseHook 

# Return sensor value
from airflow.sensors.base import PokeReturnValue

# Other imports
import requests
from datetime import datetime


# ---------------------------------------------------------------------------------------------- #
# Define the DAG using the @dag decorator
@dag(
    start_date=datetime(2023, 1, 1),  # The start date for the DAG
    schedule_interval='@daily',  # Schedule the DAG to run daily
    catchup=False,  # Disable catchup to prevent backfilling DAG runs
    tags=['stock_market']  # Tags for categorizing the DAG also to search using it
)

# dag function
def stock_market_dag():

    # Define a task to check if the API is available
    # The task is a sensor that checks the API every 30 seconds and times out after 3600 seconds
    @task.sensor(poke_interval=30, timeout=3600, mode='poke')
    def is_api_available() -> PokeReturnValue:
        # Get the connection details for 'stock_api' which we created on UI (Admin -> Connections)
        api = BaseHook.get_connection('stock_api')
        # Construct the API URL using the host and endpoint from the connection details
        url = f"{api.host}{api.extra_dejson['endpoint']}"
        # Make a GET request to the API
        response = requests.get(url, headers=api.extra_dejson['headers'])
        # Check if the API response contains data (condition is True if no data)
        condition = response.json()['finance']['result'] is None
        # Return the sensor result and the API URL (via XCom)
        return PokeReturnValue(is_done=condition, xcom_value=url)
    
    # Call the sensor task to check API availability
    is_api_available()


# ---------------------------------------------------------------------------------------------- #
# Initialize the DAG by calling the DAG function
stock_market_dag()

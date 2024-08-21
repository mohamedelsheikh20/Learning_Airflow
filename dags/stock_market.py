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

# import operator
from airflow.operators.python import PythonOperator

# import docker operator to manage seperated containers (airflow container and spark container)
from airflow.providers.docker.operators.docker import DockerOperator


# imports to deal with astro-sdk (to handle moving data easily)
from astro import sql as aql
from astro.files import File
from astro.sql.table import Table, Metadata

# Other imports
import requests
import sqlalchemy
from datetime import datetime


# get the functions we need to use from other files
from include.stock_market.tasks import _get_stock_prices, _store_prices, _get_formatted_prices_from_minio


# ---------------------------------------------------------------------------------------------- #

# certain search we need to find
SYMBOL='AAPL'

# ---------------------------------------------------------------------------------------------- #
# Define the DAG using the @dag decorator
@dag(
    start_date=datetime(2023, 1, 1),  # The start date for the DAG
    schedule_interval='@daily',  # Schedule the DAG to run daily
    catchup=False,  # Disable catchup to prevent backfilling DAG runs
    tags=['stock_market']  # Tags for categorizing the DAG also to search using it
)

# ---------------------------------------------------------------------------------------------- #
# dag function
def stock_market_dag():

    # ****************************************************************************************** #
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
    

    # ****************************************************************************************** #
    # Define a task to get the data from API
    # use operator here to mix it with the operator of the docker
    get_stock_prices = PythonOperator(
        task_id='get_stock_prices',
        python_callable=_get_stock_prices,  # create seperated file to add all functions on it (better)

        # args (dict -> keys is the args names, values is the args values)
        # `url` and `symbol` are the arguments passed to the _get_stock_prices function.

        # '{{ ti.xcom_pull(task_ids="is_api_available") }}' using the task with id is_api_available while running
        # uses Jinja templating to dynamically pull data from task with task_id `is_api_available` using Airflow's XCom (cross-communication).
        op_kwargs={'url': '{{ ti.xcom_pull(task_ids="is_api_available") }}', 'symbol': SYMBOL}
    )

    # ****************************************************************************************** #
    # Define a task to get the store returned data into store (in our case it is Minio)
    store_prices = PythonOperator(
        task_id='store_prices',
        python_callable=_store_prices,
        op_kwargs={'prices': '{{ ti.xcom_pull(task_ids="get_stock_prices") }}'},
    )

    # ****************************************************************************************** #
    # Define a task to (convert JSON into CSV) using spark other container   ( check transformation on spark)
    format_prices = DockerOperator(
        task_id='format_prices',  # Unique identifier for this task within the DAG
        max_active_tis_per_dag=1,  # Limit to one active instance of this task per DAG run
        image='airflow/spark-app',  # Docker image to use for this task, which connects to the Spark container
        container_name='trigger_job',  # Name of the container that will be created for this task
        environment={  # Environment variables to pass to the container
            'SPARK_APPLICATION_ARGS': '{{ ti.xcom_pull(task_ids="store_prices")}}'  # Pass the output from the 'store_prices' task to the container
        },
        api_version='auto',  # Automatically detect the Docker API version
        auto_remove=True,  # Remove the container after the task is finished
        docker_url='tcp://docker-proxy:2375',  # Docker daemon socket to use (specified in the yaml file)
        network_mode='container:spark-master',  # Network mode to use; shares the network with 'spark-master' container
        tty=True,  # Allocate a pseudo-TTY for the container (useful for debugging)
        xcom_all=False,  # Only push the last line of the log to XCom (default behavior)
        mount_tmp_dir=False  # Do not mount a temporary directory in the container
    )


    # ****************************************************************************************** #
    # task to get the csv file path from minio 
    get_formatted_csv = PythonOperator(
    task_id='get_formatted_csv',
    python_callable=_get_formatted_prices_from_minio, 
    op_kwargs={'location': '{{ ti.xcom_pull(task_ids="store_prices") }}'},
    )

    # ****************************************************************************************** #
    # load data to postgress using astro-sdk
    load_to_dw = aql.load_file(
        task_id='load_to_dw',
        input_file=File(path='{{ ti.xcom_pull(task_ids="get_formatted_csv") }}', conn_id='minio'),
        output_table=Table(
            name='stock_prices',
            conn_id='postgres',
            metadata=Metadata(schema='public'),
            # columns=[ # the order matters!
            #     sqlalchemy.Column('timestamp', sqlalchemy.BigInteger, primary_key=True),
            #     sqlalchemy.Column('close', sqlalchemy.Float),
            #     sqlalchemy.Column('high', sqlalchemy.Float),
            #     sqlalchemy.Column('low', sqlalchemy.Float),
            #     sqlalchemy.Column('open', sqlalchemy.Float),
            #     sqlalchemy.Column('volume', sqlalchemy.Integer),
            #     sqlalchemy.Column('date', sqlalchemy.Date),
            # ]
        )
    )


    # Call the sensor task to check API availability in (only done with decrator @)
    # >> what to be run after the next the previous one 
    is_api_available() >> get_stock_prices >> store_prices >> format_prices >> get_formatted_csv >> load_to_dw


# ---------------------------------------------------------------------------------------------- #
# Initialize the DAG by calling the DAG function
stock_market_dag()

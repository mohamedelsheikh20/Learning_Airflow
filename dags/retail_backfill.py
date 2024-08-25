# -------------------------------------- this is one DAG -------------------------------------- #
'''
This dag is used to show us:
    1- the schedule parameters used.  
'''
# -------------------------------------- this is one DAG -------------------------------------- #



from airflow.decorators import dag, task
from datetime import datetime

@dag(
    # DAG Start date `Mandatory` (old date, so it will run all old dags)
    start_date=datetime(2024, 1, 1),

    # `default is daily` Daily = every day at the mid night, can be @weekly
    schedule='@daily',

    # means to run all DAGs in periods which didn't run on it (like if you make a DAG pause)
    catchup=False,  # False means that I don't want to run all un-ran DAGs

    # 
    tags=['test']
)

def retail_backfill():
    
    @task
    def start():
        print('Hi')
        
    start()
    
retail_backfill()
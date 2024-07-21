from minio import Minio
from airflow.hooks.base import BaseHook


# minio is AWS (Amazon webservices)
def get_minio_client():
    # get the connection from the Airflow UI (must be created in the Airflow website)
    minio = BaseHook.get_connection('minio')

    # we can print to check data into the log in the docker
    # print(f'---***---minio data is:\n{minio}')
    endpoint=minio.extra_dejson['endpoint_url'].split('//')[1]
    print(f'---***---minio endpoint_url is: {endpoint}')
    print(f'---***---minio login is: {minio.login}')
    print(f'---***---minio password is: {minio.password}')

    
    client = Minio(
        # endpoint=minio.extra_dejson['endpoint_url'].split('//')[1],
        "minio:9000",   # using GPT as it is not working 
        # (login / password) those are the default fields that any connection has.
        access_key=minio.login,
        secret_key=minio.password,
        secure=False
    )
    return client
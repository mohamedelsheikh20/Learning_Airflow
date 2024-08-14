from minio import Minio
from airflow.hooks.base import BaseHook


# minio is AWS (Amazon webservices)
def get_minio_client():
    # get the connection from the Airflow UI (must be created in the Airflow website)
    minio = BaseHook.get_connection('minio')

    # we can print to check data into the log in the docker
    endpoint=minio.extra_dejson['endpoint_url'].split('//')[1]
    print(f'----***----minio endpoint_url is: {endpoint}')    
    print(f'----***----minio login is: {minio.login}')
    print(f'----***----minio password is: {minio.password}')


    client = Minio(
        endpoint=endpoint,
        # (login / password) those are the default fields that any connection has.
        access_key=minio.login, #minio['AWS_ACCESS_KEY_ID'],  
        secret_key=minio.password, #minio['AWS_SECRET_ACCESS_KEY'],  
        secure=False
    )
    
    return client
import os
import connection
import sqlparse
import pandas as pd
from datetime import datetime
from pywebhdfs.webhdfs import PyWebHdfsClient


if __name__ == '__main__':
    print('[INFO] Service ETL is Starting ...')
    
    # connection data source
    conf = connection.config('marketplace_prod')
    conn, engine = connection.psql_conn(conf, 'DataSource')
    cursor = conn.cursor()

    # connection dwh hadoop
    conf_hadoop = connection.config('hadoop')
    client_hadoop = connection.hadoop_conn(conf_hadoop)

    # get query string
    path_query = os.getcwd()+'/query/'
    query = sqlparse.format(
        open(path_query+'query.sql', 'r').read(), strip_comments=True
    ).strip()

    # get schema dwh design
    path_dwh_design = os.getcwd()+'/query/'
    dwh_design = sqlparse.format(
        open(path_dwh_design+'dwh_design.sql', 'r').read(), strip_comments=True
    ).strip()

    try:
        # get data
        print('[INFO] Service ETL is Running ...')
        df = pd.read_sql(query, engine)

        # upload file to hadoop as DWH
        filetime = datetime.now().strftime('%Y%m%d')
        
        my_file = f'dim_orders_{filetime}_tommy.csv'
        my_file_with_path = f'/digitalskola/project4/{my_file}'
        with client_hadoop.write(my_file_with_path, encoding='utf-8') as writer:
            df.to_csv(writer, index=False)
        print(f"[INFO] Upload Data in HADOOP Success .....")

        # get data from hadoop for create data mart
        print(f"[INFO] Get Data in HADOOP .....")
        hdfs=PyWebHdfsClient(host='hadoop-server',port='9870', user_name='hduser')
        filetime = datetime.now().strftime('%Y%m%d')
        data = hdfs.read_file(str(my_file_with_path))
        data = data.decode().split('\n')
        data_list = []
        for item in data:
            item = item.replace('\r', '')
            if item != '':
                data_list.append(item.split(','))
        pd.DataFrame(data_list[1:], columns=data_list[0]).to_csv(f'output/{my_file}', index=False)
        os.system(f'python mapReduce.py output/{my_file} > output/Wordercount_output_hadoop_map.txt')
        print(f"[INFO] Download Data in HADOOP Success and Created file mart.....")

        print('[INFO] Service ETL is Success ...')
    except Exception as e:
        print(e)
        print('[INFO] Service ETL is Failed ...')
        
    
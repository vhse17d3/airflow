from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta

# Định nghĩa DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 8, 6),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'fetch_weather_data',
    default_args=default_args,
    description='A DAG to fetch weather data from an API',
    schedule_interval='@daily',
    catchup=False,  # Để tránh chạy lại các DAG cũ
)

# Task để gọi API
fetch_weather_data = SimpleHttpOperator(
    task_id='fetch_weather_data',
    http_conn_id='my_http_connection',  # ID của kết nối HTTP được cấu hình trong Airflow
    endpoint='data/2.5/weather',
    method='GET',
    data={
        'q': 'Hanoi,vn',
        'appid': 'd388399437dacd258168cb4ee2883d4a',
        'lang': 'vi'
    },
    headers={"Content-Type": "application/json"},
    response_check=lambda response: response.json().get("weather") is not None,  # Kiểm tra phản hồi
    dag=dag,
)

fetch_weather_data

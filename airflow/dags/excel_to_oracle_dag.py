from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.base_hook import BaseHook
from airflow.utils.dates import days_ago
import pandas as pd
import cx_Oracle
import re
from unidecode import unidecode
import json

# Danh sách các file Excel với đường dẫn tuyệt đối
EXCEL_FILES = [
    '/opt/airflow/data/KPI Template.xlsx',
    '/opt/airflow/data/Modeling and DAX.xlsx'
]

def clean_table_name(name):
    # Loại bỏ dấu tiếng Việt và thay thế ký tự đặc biệt bằng gạch dưới
    name = unidecode(name)  # Chuyển đổi tiếng Việt thành không dấu
    name = re.sub(r'[^\w\s]', '_', name)  # Thay thế các ký tự không phải là chữ cái, số hoặc khoảng trắng
    name = re.sub(r'\s+', '_', name)      # Thay thế khoảng trắng liên tiếp bằng gạch dưới
    return name.upper()

def get_oracle_column_type(dtype):
    # Xác định kiểu dữ liệu Oracle tương ứng với kiểu dữ liệu của pandas
    if pd.api.types.is_integer_dtype(dtype):
        return 'NUMBER'
    elif pd.api.types.is_float_dtype(dtype):
        return 'FLOAT'
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return 'DATE'
    else:
        return 'VARCHAR2(4000)'

def create_table_from_df(cursor, df, table_name):
    # Tạo câu lệnh CREATE TABLE từ DataFrame
    columns = ', '.join([f'"{col.replace(" ", "_").upper()}" {get_oracle_column_type(df[col].dtype)}' for col in df.columns])
    create_table_sql = f"CREATE TABLE {table_name} ({columns})"
    try:
        cursor.execute(create_table_sql)
    except cx_Oracle.DatabaseError as e:
        # Nếu bảng đã tồn tại, không làm gì cả
        if 'ORA-00955' not in str(e):
            raise e

def generate_insert_sql(table_name, df):
    columns = ', '.join([f'"{col.replace(" ", "_").upper()}"' for col in df.columns])
    values = ', '.join([f":{i+1}" for i in range(len(df.columns))])
    return f"INSERT INTO {table_name} ({columns}) VALUES ({values})"

def load_excel_to_oracle(**kwargs):
    # Lấy thông tin kết nối từ Airflow
    conn_id = 'Connection_bai_test'
    conn = BaseHook.get_connection(conn_id)
    extra = json.loads(conn.extra)
    service_name = extra.get('service_name', 'ORCLPDB')  # Lấy service_name từ extra hoặc dùng giá trị mặc định

    # Tạo kết nối Oracle
    dsn = cx_Oracle.makedsn(conn.host, conn.port, service_name=service_name)
    connection = cx_Oracle.connect(user=conn.login, password=conn.password, dsn=dsn)
    
    try:
        for file_path in EXCEL_FILES:
            # Đọc tất cả các sheet từ file Excel
            excel_data = pd.ExcelFile(file_path)
            
            for sheet_name in excel_data.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Chuyển đổi các kiểu dữ liệu cột trong DataFrame để phù hợp với Oracle
                for col in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df[col]):
                        df[col] = pd.to_datetime(df[col])
                    elif pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = pd.to_numeric(df[col])
                    else:
                        df[col] = df[col].astype(str)
                
                # Tạo cursor và kiểm tra xem bảng đã tồn tại chưa
                cursor = connection.cursor()
                table_name = clean_table_name(sheet_name)  # Đặt tên bảng sau khi làm sạch
                
                # Tạo bảng nếu nó chưa tồn tại
                create_table_from_df(cursor, df, table_name)
                
                # Định dạng câu lệnh INSERT theo tên bảng và cột phù hợp
                insert_sql = generate_insert_sql(table_name, df)
                print(f"Executing SQL: {insert_sql}")  # In ra câu lệnh SQL để kiểm tra
                
                for index, row in df.iterrows():
                    try:
                        cursor.execute(insert_sql, tuple(row))
                    except Exception as e:
                        print(f"Error inserting row {index}: {e}")
                
                connection.commit()
    finally:
        connection.close()

# Định nghĩa DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

dag = DAG(
    'excel_to_oracle_dag',
    default_args=default_args,
    description='A DAG to load multiple Excel files into Oracle',
    schedule_interval='0 10 * * *',  # Lịch trình chạy DAG mỗi ngày lúc 10:00
    start_date=days_ago(1),
    catchup=False,
)

# Tạo task để tải dữ liệu từ Excel vào Oracle
load_task = PythonOperator(
    task_id='load_excel_to_oracle',
    python_callable=load_excel_to_oracle,
    provide_context=True,
    dag=dag,
)

load_task

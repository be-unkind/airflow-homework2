import requests

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from airflow.utils.task_group import TaskGroup
from airflow.utils.dates import days_ago

from bs4 import BeautifulSoup
from easyocr import Reader

def image_scraping():
    response = requests.get(Variable.get('SOURCE'))
    soup = BeautifulSoup(response.content, 'html.parser')
    images = set(img['src'] for img in soup.find_all('img') if 'src' in img.attrs)

    hook = PostgresHook(postgres_conn_id='new_db_conn')
    existing_images = {row[0] for row in hook.get_records("SELECT link FROM links")}
    new_images = images - existing_images

    for image in new_images:
        hook.run("INSERT INTO image_links (image_url, processed) VALUES (%s, false)", parameters=(image,))

def ocr_processing():
    hook = PostgresHook(postgres_conn_id='new_db_conn')
    result = hook.get_records("SELECT link FROM links WHERE processed = false")
    links = []

    for row in result:
        image_link = row[0]
        reader = Reader(['en'])
        try:
            ocr_results = reader.readtext(image_link)
        except:
            continue
        
    return links


def enrich_data():
    return

with DAG(dag_id="marketing_dag", schedule_interval="@daily", start_date=days_ago(3), catchup=True) as dag: 
    create_links_table_task = PostgresOperator(task_id="create_links_table",
                                          postgres_conn_id="new_db_conn",
                                          sql="""
                                              CREATE TABLE IF NOT EXISTS links (
                                                 id SERIAL PRIMARY KEY,
                                                 link TEXT,
                                                 processed BOOLEAN
                                                 );
                                          """
                                          )
    
    create_companies_table_task = PostgresOperator(task_id="create_companies_table",
                                              postяgres_conn_id="new_db_conn",
                                              sql="""
                                                  CREATE TABLE IF NOT EXISTS companies (
                                                     );
                                              """
                                              )
    
    image_scraping_task = PythonOperator(
        task_id='scrape_images',
        python_callable=image_scraping,
        )
    
    ocr_processing_task = PythonOperator(
        task_id='ocr_processing',
        python_callable=ocr_processing
    )

    data_enrichment_task = PythonOperator(
        task_id='data_enrichment',
        python_callable=enrich_data,
    )

    create_links_table_task >> create_companies_table_task >> image_scraping_task >> ocr_processing_task >> data_enrichment_task
    

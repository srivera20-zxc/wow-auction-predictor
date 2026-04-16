FROM apache/airflow:2.7.3-python3.11

# Install our project's dependencies on top of the base Airflow image
USER airflow
RUN pip install --no-cache-dir \
    requests==2.31.0 \
    python-dotenv==1.0.0 \
    psycopg2-binary==2.9.9 \
    sqlalchemy==2.0.0 \
    pandas==2.1.0

# Make src/ importable inside Airflow tasks
ENV PYTHONPATH=/opt/airflow

-- Creates the databases and users needed by each service.
-- This runs automatically when the postgres container first starts.

-- Airflow metadata database (used internally by Airflow)
CREATE USER airflow WITH PASSWORD 'airflow';
CREATE DATABASE airflow OWNER airflow;

-- Our auction data database
CREATE USER wow_user WITH PASSWORD 'wow_pass';
CREATE DATABASE wow_auctions OWNER wow_user;

-- MLflow experiment tracking database
CREATE USER mlflow WITH PASSWORD 'mlflow';
CREATE DATABASE mlflow OWNER mlflow;

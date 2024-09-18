# Use the base Apache Airflow image
FROM apache/airflow:2.7.3
RUN pip install --upgrade pip
# Set environment variables for the Oracle Instant Client
ENV ORACLE_HOME=/opt/oracle/instantclient
ENV LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
ENV PATH=$ORACLE_HOME:$PATH

# Switch to the root user temporarily
USER root

# Install required packages
RUN apt-get update && apt-get install -y \
    unzip \
    libaio1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create the Oracle directory with proper permissions
RUN mkdir -p /opt/oracle && chown -R airflow: /opt/oracle

# Switch back to a non-root user (e.g., "airflow")
USER airflow

# Install Python packages required for Oracle client and Airflow Oracle provider
RUN pip install cx_Oracle apache-airflow-providers-oracle pandas sqlalchemy

# Download and install the Oracle Instant Client
RUN curl -L -o /tmp/instantclient-basic-linux.x64-19.11.0.0.0dbru.zip https://download.oracle.com/otn_software/linux/instantclient/1911000/instantclient-basic-linux.x64-19.11.0.0.0dbru.zip && \
    curl -L -o /tmp/instantclient-sdk-linux.x64-19.11.0.0.0dbru.zip https://download.oracle.com/otn_software/linux/instantclient/1911000/instantclient-sdk-linux.x64-19.11.0.0.0dbru.zip && \
    unzip /tmp/instantclient-basic-linux.x64-19.11.0.0.0dbru.zip -d /opt/oracle && \
    unzip /tmp/instantclient-sdk-linux.x64-19.11.0.0.0dbru.zip -d /opt/oracle && \
    ln -s /opt/oracle/instantclient_19_11 $ORACLE_HOME && \
    rm /tmp/instantclient-basic-linux.x64-19.11.0.0.0dbru.zip /tmp/instantclient-sdk-linux.x64-19.11.0.0.0dbru.zip

# Set environment variables for Oracle Instant Client
ENV ORACLE_VERSION=19.11

# Ensure the entrypoint is correct
ENTRYPOINT ["/entrypoint"]
CMD ["webserver"]

ARG SPARK_VERSION=3.5.5
ARG AIRFLOW_VERSION=2.10.5

FROM apache/spark:${SPARK_VERSION} AS spark

FROM apache/airflow:${AIRFLOW_VERSION}

USER root

COPY --from=spark /opt/spark /opt/spark

RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV SPARK_HOME=/opt/spark
ENV HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
ENV YARN_CONF_DIR=/opt/hadoop/etc/hadoop
ENV PATH=/opt/spark/bin:/opt/spark/sbin:${PATH}
ENV PYSPARK_PYTHON=python3

USER airflow

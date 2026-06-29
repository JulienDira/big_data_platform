ARG SPARK_VERSION=3.5.5
FROM apache/spark:${SPARK_VERSION}

USER root
COPY infra/images/pyspark-requirements.txt /tmp/pyspark-requirements.txt

RUN pip3 install --no-cache-dir -r /tmp/pyspark-requirements.txt \
    && rm -f /tmp/pyspark-requirements.txt

ENV SPARK_HOME=/opt/spark
ENV HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
ENV YARN_CONF_DIR=/opt/hadoop/etc/hadoop
ENV PATH=/opt/spark/bin:/opt/spark/sbin:${PATH}
ENV PYSPARK_PYTHON=python3

CMD ["bash"]

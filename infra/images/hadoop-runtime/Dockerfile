ARG HADOOP_VERSION=3.4.1
ARG MINIFORGE_VERSION=24.11.3-0
ARG PYTHON_VERSION=3.10

FROM condaforge/miniforge3:${MINIFORGE_VERSION} AS python-runtime
ARG MINIFORGE_VERSION=24.11.3-0
ARG PYTHON_VERSION=3.10

COPY infra/images/pyspark-requirements.txt /tmp/pyspark-requirements.txt

RUN set -eux; \
    conda install -y "python=${PYTHON_VERSION}" pip; \
    python -m pip install --no-cache-dir -r /tmp/pyspark-requirements.txt; \
    conda clean -afy; \
    rm -f /tmp/pyspark-requirements.txt

FROM apache/hadoop:${HADOOP_VERSION}

USER root

ENV HADOOP_HOME=/opt/hadoop
ENV HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
ENV YARN_CONF_DIR=/opt/hadoop/etc/hadoop
ENV CONDA_HOME=/opt/conda
ENV PATH=/opt/conda/bin:/opt/hadoop/bin:/opt/hadoop/sbin:${PATH}
ENV PYSPARK_PYTHON=/opt/conda/bin/python

COPY --from=python-runtime /opt/conda /opt/conda

RUN set -eux; \
    ln -sf "${CONDA_HOME}/bin/python" /usr/local/bin/python3; \
    ln -sf "${CONDA_HOME}/bin/pip" /usr/local/bin/pip3

ENTRYPOINT []
CMD ["bash"]

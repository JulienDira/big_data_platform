ARG HIVE_VERSION=3.1.3
FROM apache/hive:${HIVE_VERSION}

USER root
RUN rm -f /opt/hive/lib/postgresql-*.jar /opt/hive/lib/postgresql.jar
ADD --chmod=0644 \
    https://jdbc.postgresql.org/download/postgresql-42.7.4.jar \
    /opt/hive/lib/postgresql.jar
USER hive

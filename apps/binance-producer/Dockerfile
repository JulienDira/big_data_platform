ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim

WORKDIR /workspace
ARG INSTALL_AWS_DEPS=false
COPY apps/binance-producer/requirements.txt /tmp/requirements.txt
COPY apps/binance-producer/requirements-aws.txt /tmp/requirements-aws.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && if [ "$INSTALL_AWS_DEPS" = "true" ]; then \
        pip install --no-cache-dir -r /tmp/requirements-aws.txt; \
    fi

COPY apps/binance-producer /workspace/apps/binance-producer
COPY contracts /workspace/contracts

ENV CONTRACT_PATH=/workspace/contracts/market-candle/v1.avsc
CMD ["python", "/workspace/apps/binance-producer/main.py"]

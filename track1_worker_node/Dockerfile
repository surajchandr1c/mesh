FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# llama-cpp-python builds native bindings during installation.
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --system workeruser \
    && useradd --system --gid workeruser --create-home \
        --home-dir /home/workeruser --shell /usr/sbin/nologin workeruser

COPY --chown=workeruser:workeruser main.py engine.py monitor.py ./

USER workeruser

CMD ["python", "main.py"]

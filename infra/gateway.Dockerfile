FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md /app/
COPY gateway /app/gateway
COPY schemas /app/schemas
RUN pip install --no-cache-dir "git+https://github.com/globalpocket/thalamus.git"
RUN pip install --no-cache-dir .
CMD ["python", "-c", "import asyncio; from gateway.server import run_gateway; asyncio.run(run_gateway())"]

FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md /app/
COPY gateway /app/gateway
COPY schemas /app/schemas
RUN pip install --no-cache-dir .
CMD ["python", "-c", "import asyncio; from gateway.server import run_gateway; asyncio.run(run_gateway())"]


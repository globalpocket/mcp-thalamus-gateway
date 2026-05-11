FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md /app/
COPY subagent /app/subagent
COPY schemas /app/schemas
RUN pip install --no-cache-dir "git+https://github.com/globalpocket/thalamus.git"
RUN pip install --no-cache-dir .
CMD ["python", "-m", "subagent.main"]

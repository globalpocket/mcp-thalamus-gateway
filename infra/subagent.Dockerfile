FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md /app/
COPY subagent /app/subagent
COPY schemas /app/schemas
RUN pip install --no-cache-dir .
CMD ["python", "-m", "subagent.main"]


FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "openenv-core[core]>=0.2.1" \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.29.0" \
    "pydantic>=2.0"

COPY ticket_triage_env/ ./ticket_triage_env/
COPY server/ ./server/
COPY openenv.yaml .

ENV PYTHONPATH=/app
ENV TICKET_TRIAGE_TASK=classify
ENV PORT=7860

EXPOSE 7860

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]

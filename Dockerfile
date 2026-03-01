# Leviathan Super Brain Dev Team v3.0
# Multi-model AI software engineering team
# Claude (Architect) + DeepSeek (Engineer) + Grok (Reviewer) + Gemini (Researcher) + DeepSeek-R1 (QA)
FROM python:3.11-slim

RUN pip install --no-cache-dir flask gunicorn requests

WORKDIR /app
COPY team_server.py /app/team_server.py

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "180", "--workers", "2", "--threads", "4", "team_server:app"]

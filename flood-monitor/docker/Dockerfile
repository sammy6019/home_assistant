FROM python:3.11-slim
WORKDIR /app
RUN pip install requests
COPY api.py .
CMD ["python3", "-u", "api.py"]

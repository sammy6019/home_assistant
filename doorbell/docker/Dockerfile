FROM python:3.11-slim
WORKDIR /app
RUN pip install flask requests anthropic pillow
COPY doorbell_server.py .
CMD ["python3", "-u", "doorbell_server.py"]

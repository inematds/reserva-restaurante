FROM python:3-slim
WORKDIR /app
COPY reserva VERSION ./
COPY src/ ./src/
COPY web/ ./web/
COPY exemplos/ ./exemplos/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python3 -c "import json, urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/saude', timeout=3))['ok']"
CMD ["./reserva", "serve", "--host", "0.0.0.0", "--porta", "8080", "--dados", "/dados"]

FROM python:3.12-slim

LABEL maintainer="Softreck / Prototypowanie.pl"
LABEL description="RP2040-One HID Keypad Web Configurator"

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi>=0.110.0 \
    uvicorn[standard]>=0.29.0 \
    jinja2>=3.1.0 \
    python-multipart>=0.0.9 \
    aiofiles>=23.0

COPY firmware/ /app/firmware/
COPY web/ /app/web/
COPY README.md /app/

RUN mkdir -p /app/output

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/')" || exit 1

CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8080"]

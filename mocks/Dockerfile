FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mock_tei.py mock_vllm.py ./
# SERVICE env selects which mock to run (tei | vllm)
ENV SERVICE=tei
CMD ["sh", "-c", "if [ \"$SERVICE\" = vllm ]; then uvicorn mock_vllm:app --host 0.0.0.0 --port 8000; else uvicorn mock_tei:app --host 0.0.0.0 --port 80; fi"]

FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git
RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install torch==1.13.1+cpu torchaudio==0.13.1 --extra-index-url https://download.pytorch.org/whl/cpu
RUN mkdir -p /app/audio

COPY . .

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    libasound2 \
    libasound2-plugins \
    libportaudio2 \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    numpy \
    sounddevice \
    plotille

COPY eb.py .

ENTRYPOINT ["python", "eb.py"]


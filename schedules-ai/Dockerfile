FROM pytorch/pytorch:2.4.1-cuda11.8-cudnn9-runtime AS base

WORKDIR /app

RUN apt-get update

FROM base as dev

RUN apt-get install curl -y

COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "python3 -c 'import torch; print(torch.__version__); print(torch.cuda.is_available())' && python3 api/app.py"]

CMD python3 api/app.py

FROM base as prod

COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD python3 api/app.py
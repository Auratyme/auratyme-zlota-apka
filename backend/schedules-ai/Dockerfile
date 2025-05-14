FROM pytorch/pytorch:2.4.1-cuda11.8-cudnn9-runtime AS base

WORKDIR /app

RUN apt-get update

FROM base AS dev

RUN apt-get install curl -y

# Copy requirements file
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a script to run both scheduler and API server
RUN echo '#!/bin/bash\n\n# Uruchom scheduler w tle i przekieruj jego wyjście do pliku log\npython3 -m src.core.scheduler > /app/scheduler.log 2>&1 &\n\n# Zapisz PID schedulera\necho $! > /app/scheduler.pid\n\n# Poczekaj 2 sekundy, aby scheduler mógł się uruchomić\nsleep 2\n\n# Wyświetl ostatnie 10 linii logu schedulera\necho "Ostatnie linie logu schedulera:"\ntail -n 10 /app/scheduler.log\n\n# Uruchom API server w trybie foreground\necho "Uruchamianie API serwera..."\npython3 -m api.server\n' > /app/run.sh && chmod +x /app/run.sh

# Run both scheduler and API server

CMD ["python3", "-m", "api2.main"]

# CMD ["/app/run.sh"]

FROM base AS prod

# Copy requirements file
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a script to run both scheduler and API server
RUN echo '#!/bin/bash\n\n# Uruchom scheduler w tle i przekieruj jego wyjście do pliku log\npython3 -m src.core.scheduler > /app/scheduler.log 2>&1 &\n\n# Zapisz PID schedulera\necho $! > /app/scheduler.pid\n\n# Poczekaj 2 sekundy, aby scheduler mógł się uruchomić\nsleep 2\n\n# Wyświetl ostatnie 10 linii logu schedulera\necho "Ostatnie linie logu schedulera:"\ntail -n 10 /app/scheduler.log\n\n# Uruchom API server w trybie foreground\necho "Uruchamianie API serwera..."\npython3 -m api.server\n' > /app/run.sh && chmod +x /app/run.sh

# Run both scheduler and API server
CMD ["/app/run.sh"]
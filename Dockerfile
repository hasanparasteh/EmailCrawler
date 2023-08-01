FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt /app

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Install the latest version of Firefox and geckodriver
RUN apt-get update && \
    apt-get install -y xvfb gnupg wget curl unzip firefox-esr && \
    wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz && \
    tar -xvzf geckodriver-v0.33.0-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/ && \
    rm geckodriver-v0.33.0-linux64.tar.gz

COPY main.py /app
COPY .env.docker /app/.env

RUN mkdir /app/html

# Set the environment variables for running Firefox with Selenium
ENV DISPLAY=:99
ENV TZ=UTC

# Run the command to start Xvfb, which provides a virtual display for Firefox
CMD Xvfb :99 -screen 0 1920x1080x24 && python main.py
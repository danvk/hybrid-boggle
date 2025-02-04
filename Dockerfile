FROM python:3.13.1
WORKDIR /usr/local/app

RUN git clone https://github.com/danvk/hybrid-boggle.git && \
    cd hybrid-boggle && \
    python -m venv venv && \
    source venv/bin/activate && \
    pip install poetry && \
    poetry install && \
    ./build.sh
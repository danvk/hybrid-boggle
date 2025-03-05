FROM python:3.13.1
WORKDIR /usr/local/app
ARG GIT_SHA
LABEL git-sha=$GIT_SHA

RUN git clone https://github.com/danvk/hybrid-boggle.git && \
    cd hybrid-boggle && \
    git reset --hard $GIT_SHA && \
    python -m venv venv && \
    . venv/bin/activate && \
    pip install poetry && \
    poetry install && \
    ./build.sh

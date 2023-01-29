FROM python:3.11.1

WORKDIR /usr/src/app

ARG PKG_VERSION=1

COPY dist/*.tar.gz ./

RUN python -m pip install $(echo *.tar.gz)[all]

CMD [ "python", "-c", "import dcqc" ]

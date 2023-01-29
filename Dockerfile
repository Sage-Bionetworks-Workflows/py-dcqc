FROM python:3.11.1

WORKDIR /usr/src/app

ARG PKG_VERSION=1

RUN pip install --no-cache-dir pipenv

COPY setup.* Pipfile* ./
COPY src ./src/

RUN SETUPTOOLS_SCM_PRETEND_VERSION_FOR_SAGETASKS=${PKG_VERSION} \
    python -m pip install .[all]

CMD [ "python", "-c", "import dcqc" ]

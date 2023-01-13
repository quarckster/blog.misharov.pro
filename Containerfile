FROM registry.fedoraproject.org/fedora:37

ENV PELICAN_VENV=/pelican_venv

RUN dnf install -y python3.10 make && \
    python3.10 -m venv ${PELICAN_VENV} && \
    dnf clean all

ENV PATH=${PATH}:${PELICAN_VENV}/bin/

RUN --mount=type=bind,target=/mnt \
    python -m pip install --no-cache-dir wheel && \
    python -m pip install --no-cache-dir -r /mnt/requirements.txt

USER 1001

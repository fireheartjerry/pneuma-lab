FROM docker.io/vllm/vllm-openai@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90

ARG SOURCE_COMMIT
LABEL org.opencontainers.image.source="https://github.com/fireheartjerry/pneuma-lab" \
      org.opencontainers.image.revision="${SOURCE_COMMIT}" \
      org.opencontainers.image.title="Pneuma C160 qualification worker" \
      org.opencontainers.image.base.digest="sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90"

# The upstream serving image is immutable but its Ubuntu packages age. Apply
# every security update available at build time; the resulting ECR digest and
# scan receipt, not this mutable package operation, are the execution pin.
RUN sed -i \
        -e 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g' \
        -e 's|http://security.ubuntu.com|https://security.ubuntu.com|g' \
        /etc/apt/sources.list /etc/apt/sources.list.d/*.list \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        curl \
        unzip \
    && DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade --yes \
    && DEBIAN_FRONTEND=noninteractive apt-get purge --yes --auto-remove \
        ffmpeg \
        libavcodec58 \
        libavdevice58 \
        libavfilter7 \
        libavformat58 \
        libavutil56 \
        libpostproc55 \
        libswresample3 \
        libswscale5 \
    && curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
        https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip \
        --output /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install --install-dir /usr/local/aws-cli --bin-dir /usr/local/bin \
    && rm -rf /tmp/aws /tmp/awscliv2.zip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONHASHSEED=0 \
    TZ=UTC \
    PNEUMA_SUBJECT_MODEL=Qwen/Qwen3.6-35B-A3B-FP8 \
    PNEUMA_SUBJECT_REVISION=95a723d08a9490559dae23d0cff1d9466213d989 \
    PNEUMA_SIMULATOR_MODEL=Qwen/Qwen3.5-9B \
    PNEUMA_SIMULATOR_REVISION=c202236235762e1c871ad0ccb60c8ee5ba337b9a

# Ship the importable package, including the fixed two-rung admission probe.
# The image itself selects qualification mode; Batch supplies no alternate
# command and therefore cannot dispatch a scientific workload.
COPY src/pneuma_lab /opt/pneuma/pneuma_lab
COPY schemas /opt/schemas
COPY infra/docker/qualification-worker/fixed_admission_entrypoint.sh /opt/pneuma/fixed_admission_entrypoint.sh
RUN chmod 0555 /opt/pneuma/fixed_admission_entrypoint.sh \
    && test -f /opt/schemas/cloud-worker-admission-measurement.schema.json
ENV PYTHONPATH=/opt/pneuma
ENTRYPOINT ["/opt/pneuma/fixed_admission_entrypoint.sh"]

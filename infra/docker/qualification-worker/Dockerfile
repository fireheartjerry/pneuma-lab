FROM docker.io/vllm/vllm-openai@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90

ARG SOURCE_COMMIT
LABEL org.opencontainers.image.source="https://github.com/fireheartjerry/pneuma-lab" \
      org.opencontainers.image.revision="${SOURCE_COMMIT}" \
      org.opencontainers.image.title="Pneuma C160 qualification worker" \
      org.opencontainers.image.base.digest="sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90"

# The upstream serving image is immutable but its Ubuntu packages age. Apply
# every security update available at build time; the resulting ECR digest and
# scan receipt, not this mutable package operation, are the execution pin.
RUN apt-get update \
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONHASHSEED=0 \
    TZ=UTC \
    PNEUMA_SUBJECT_MODEL=Qwen/Qwen3.6-35B-A3B-FP8 \
    PNEUMA_SUBJECT_REVISION=95a723d08a9490559dae23d0cff1d9466213d989 \
    PNEUMA_SIMULATOR_MODEL=Qwen/Qwen3.5-9B \
    PNEUMA_SIMULATOR_REVISION=c202236235762e1c871ad0ccb60c8ee5ba337b9a

COPY qualification_entrypoint.py /opt/pneuma/qualification_entrypoint.py
ENTRYPOINT ["python3", "/opt/pneuma/qualification_entrypoint.py"]
CMD ["inspect"]

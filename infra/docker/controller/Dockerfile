# Step 7B base is bound by the real Step 5B input lock.  The same role image
# carries both the qualification probe and the separately gated production
# runtime; protocol selection is explicit at invocation time.
FROM vllm/vllm-openai@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90
ARG SOURCE_DATE_EPOCH=0
ENV PYTHONHASHSEED=0 TZ=UTC PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/pneuma
WORKDIR /opt/pneuma
COPY infra/docker/controller/controller.lock /opt/pneuma/controller.lock
COPY src/pneuma_lab/__init__.py /opt/pneuma/pneuma_lab/__init__.py
COPY src/pneuma_lab/cloud /opt/pneuma/pneuma_lab/cloud
COPY src/pneuma_lab/foundation/__init__.py /opt/pneuma/pneuma_lab/foundation/__init__.py
COPY src/pneuma_lab/foundation/artifacts.py /opt/pneuma/pneuma_lab/foundation/artifacts.py
COPY src/pneuma_lab/foundation/specs.py /opt/pneuma/pneuma_lab/foundation/specs.py
COPY src/pneuma_lab/resampling_null/__init__.py /opt/pneuma/pneuma_lab/resampling_null/__init__.py
COPY src/pneuma_lab/resampling_null/errors.py /opt/pneuma/pneuma_lab/resampling_null/errors.py
COPY src/pneuma_lab/resampling_null/json_io.py /opt/pneuma/pneuma_lab/resampling_null/json_io.py
COPY src/pneuma_lab/resampling_null/preflight.py /opt/pneuma/pneuma_lab/resampling_null/preflight.py
COPY src/pneuma_lab/resampling_null/types.py /opt/pneuma/pneuma_lab/resampling_null/types.py
COPY src/pneuma_lab/schemas/__init__.py /opt/pneuma/pneuma_lab/schemas/__init__.py
COPY schemas/cloud-approver-key-registry.schema.json /opt/schemas/cloud-approver-key-registry.schema.json
COPY schemas/cloud-official-study-authorization.schema.json /opt/schemas/cloud-official-study-authorization.schema.json
COPY schemas/cloud-production-controller-state.schema.json /opt/schemas/cloud-production-controller-state.schema.json
COPY schemas/cloud-production-execution-surface.schema.json /opt/schemas/cloud-production-execution-surface.schema.json
COPY schemas/cloud-production-raw-worker-output.schema.json /opt/schemas/cloud-production-raw-worker-output.schema.json
COPY schemas/cloud-production-run-spec.schema.json /opt/schemas/cloud-production-run-spec.schema.json
COPY schemas/cloud-production-worker-evidence.schema.json /opt/schemas/cloud-production-worker-evidence.schema.json
COPY schemas/cloud-production-provider-binding.schema.json /opt/schemas/cloud-production-provider-binding.schema.json
# The digest-pinned vLLM base must contain the reviewed runtime closure.  Fail
# the image build rather than discovering a missing verifier dependency at run.
RUN python3 -c "import cryptography, jsonschema"
# BuildKit before the timestamp-rewriting exporter leaves COPY-layer file and
# workdir mtimes host-dependent. Normalize this small build-owned tree so the
# image config/rootfs digest remains reproducible on the pinned AWS builder.
RUN find /opt/pneuma -xdev -exec touch --date="@${SOURCE_DATE_EPOCH}" --no-dereference {} + \
    && touch --date="@${SOURCE_DATE_EPOCH}" --no-dereference /opt
ENTRYPOINT ["python3", "-m", "pneuma_lab.cloud.production_runtime", "controller"]

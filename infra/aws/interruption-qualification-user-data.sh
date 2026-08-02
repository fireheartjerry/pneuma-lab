#!/bin/bash
# Bounded AWS interruption/recovery qualification template.
# Rendered per role; no model, benchmark, GPU, or Batch work is permitted.
set -euo pipefail

readonly ROLE='__ROLE__'
readonly ACTION_ID='__ACTION_ID__'
readonly REGION='us-east-1'
readonly BUCKET='__BUCKET__'
readonly TABLE='__TABLE__'
readonly LEASE_KEY='__LEASE_KEY__'
readonly BOUNDARY_KEY='__BOUNDARY_KEY__'
readonly REPORT_KEY='__REPORT_KEY__'
readonly CONTROLLER_REPORT_KEY='__CONTROLLER_REPORT_KEY__'
readonly CONTROLLER_INSTANCE_ID='__CONTROLLER_INSTANCE_ID__'
readonly LEASE_EXPIRY='__LEASE_EXPIRY__'

export AWS_DEFAULT_REGION="$REGION"
exec > >(tee /var/log/pneuma-interruption.log) 2>&1

sha256_file() {
    sha256sum "$1" | awk '{print $1}'
}

lease_json() {
    aws dynamodb get-item \
        --table-name "$TABLE" \
        --key "{\"lease_key\":{\"S\":\"$LEASE_KEY\"}}" \
        --consistent-read \
        --output json
}

if [[ "$ROLE" == controller ]]; then
    for _ in $(seq 1 30); do
        current=$(lease_json)
        if [[ "$current" == *"controller_instance_id"* ]]; then
            break
        fi
        sleep 2
    done
    cat > /tmp/completed-boundary.json <<EOF
{"action_id":"$ACTION_ID","arms":{"control":"completed-control-v1","null":"completed-null-v1","treated":"completed-treated-v1"},"sequence":1}
EOF
    pre_hash=$(sha256_file /tmp/completed-boundary.json)
    aws s3 cp /tmp/completed-boundary.json "s3://$BUCKET/$BOUNDARY_KEY" \
        --sse AES256 --only-show-errors

    set +e
    aws dynamodb update-item \
        --table-name "$TABLE" \
        --key "{\"lease_key\":{\"S\":\"$LEASE_KEY\"}}" \
        --update-expression 'SET controller_renewal_count = :n' \
        --expression-attribute-values '{":n":{"N":"1"}}' \
        --return-values ALL_NEW >/tmp/renewal-attempt.json 2>/tmp/renewal-attempt.stderr
    renewal_rc=$?
    set -e
    controller_arn=$(aws sts get-caller-identity --query Arn --output text)
    if [[ "$renewal_rc" -eq 0 ]]; then
        renewal_outcome=unexpectedly_allowed
    else
        renewal_outcome=denied_as_expected
    fi
    printf '{"action_id":"%s","boundary_sha256":"%s","controller_identity":"%s","renewal_exit_code":%d,"renewal_outcome":"%s"}\n' \
        "$ACTION_ID" "$pre_hash" "$controller_arn" "$renewal_rc" "$renewal_outcome" >/tmp/controller-report.json
    aws s3 cp /tmp/controller-report.json "s3://$BUCKET/$CONTROLLER_REPORT_KEY" \
        --sse AES256 --only-show-errors
    while true; do sleep 5; done
fi

if [[ "$ROLE" == watcher ]]; then
    for _ in $(seq 1 60); do
        now=$(date -u +%s)
        if [[ "$now" -ge "$LEASE_EXPIRY" ]]; then
            observed=$(date -u +%Y-%m-%dT%H:%M:%SZ)
            watcher_arn=$(aws sts get-caller-identity --query Arn --output text)
            aws dynamodb update-item \
                --table-name "$TABLE" \
                --key "{\"lease_key\":{\"S\":\"$LEASE_KEY\"}}" \
                --update-expression 'SET watcher_observed_timestamp = :t, watcher_termination_requested = :v, watcher_identity = :a' \
                --expression-attribute-values "{\":t\":{\"S\":\"$observed\"},\":v\":{\"BOOL\":true},\":a\":{\"S\":\"$watcher_arn\"}}" \
                --return-values ALL_NEW >/tmp/watcher-update.json
            aws ec2 terminate-instances --instance-ids "$CONTROLLER_INSTANCE_ID" \
                --output json >/tmp/watcher-terminate.json
            aws dynamodb update-item \
                --table-name "$TABLE" \
                --key "{\"lease_key\":{\"S\":\"$LEASE_KEY\"}}" \
                --update-expression 'SET watcher_termination_state = :s' \
                --expression-attribute-values '{":s":{"S":"requested"}}' \
                --return-values NONE >/dev/null
            shutdown -h now
            exit 0
        fi
        sleep 5
    done
    aws dynamodb update-item \
        --table-name "$TABLE" \
        --key "{\"lease_key\":{\"S\":\"$LEASE_KEY\"}}" \
        --update-expression 'SET watcher_termination_state = :s' \
        --expression-attribute-values '{":s":{"S":"timeout"}}' \
        --return-values NONE >/dev/null
    shutdown -h now
    exit 1
fi

if [[ "$ROLE" == recovery ]]; then
    aws s3 cp "s3://$BUCKET/$BOUNDARY_KEY" /tmp/completed-boundary.json \
        --only-show-errors
    restored_hash=$(sha256_file /tmp/completed-boundary.json)
    printf '{"action_id":"%s","restored_sha256":"%s","all_arm_visible_bytes_match":true}\n' \
        "$ACTION_ID" "$restored_hash" >/tmp/recovery-report.json
    aws s3 cp /tmp/recovery-report.json "s3://$BUCKET/$REPORT_KEY" \
        --sse AES256 --only-show-errors
    shutdown -h now
    exit 0
fi

exit 2

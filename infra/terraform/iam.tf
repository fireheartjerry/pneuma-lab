data "aws_iam_policy_document" "ec2_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "batch_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["batch.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "batch_service" {
  name               = "${var.name_prefix}-batch-service"
  assume_role_policy = data.aws_iam_policy_document.batch_assume.json
}

resource "aws_iam_role_policy_attachment" "batch_service" {
  role       = aws_iam_role.batch_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

data "aws_iam_policy_document" "spot_fleet_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["spotfleet.amazonaws.com"]
    }
  }
}

# Required by the managed EC2 Spot environment. This identity has no access
# to experiment data or authority; it only lets Batch launch/tag/terminate its
# own Spot Fleet capacity.
resource "aws_iam_role" "spot_fleet" {
  name               = "${var.name_prefix}-spot-fleet"
  assume_role_policy = data.aws_iam_policy_document.spot_fleet_assume.json
}

resource "aws_iam_role_policy_attachment" "spot_fleet" {
  role       = aws_iam_role.spot_fleet.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole"
}

resource "aws_iam_role" "worker" {
  name               = "${var.name_prefix}-worker"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_instance_profile" "worker" {
  name = "${var.name_prefix}-worker"
  role = aws_iam_role.worker.name
}

resource "aws_iam_role_policy_attachment" "ecs_worker" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_role_policy_attachment" "ssm_worker" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "worker" {
  statement {
    sid     = "QualificationFixtureInputs"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.artifacts.arn}/${local.qualification_artifact_prefix}/inputs/protocol.json",
      "${aws_s3_bucket.artifacts.arn}/${local.qualification_artifact_prefix}/inputs/architecture.json",
      "${aws_s3_bucket.artifacts.arn}/${local.qualification_artifact_prefix}/inputs/authorization.json",
      "${aws_s3_bucket.artifacts.arn}/${local.qualification_artifact_prefix}/inputs/image.json",
      "${aws_s3_bucket.artifacts.arn}/${local.qualification_artifact_prefix}/inputs/input-lock.json",
    ]
  }
  statement {
    sid     = "QualificationRawOutputs"
    effect  = "Allow"
    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.artifacts.arn}/${local.qualification_artifact_prefix}/outputs/worker-0/raw-measurement.json",
      "${aws_s3_bucket.artifacts.arn}/${local.qualification_artifact_prefix}/outputs/worker-1/raw-measurement.json",
    ]
  }
  statement {
    sid       = "ReadLeaseOnly"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.leases.arn]
  }
}

resource "aws_iam_role_policy" "worker" {
  name   = "bounded-experiment-access"
  role   = aws_iam_role.worker.id
  policy = data.aws_iam_policy_document.worker.json
}

resource "aws_iam_role" "watcher" {
  name               = "${var.name_prefix}-watcher"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

data "aws_iam_policy_document" "watcher" {
  statement {
    sid       = "RenewLease"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.leases.arn]
  }
  statement {
    sid       = "StopOwnedBatchWork"
    effect    = "Allow"
    actions   = ["batch:CancelJob", "batch:TerminateJob", "batch:UpdateComputeEnvironment", "batch:UpdateJobQueue"]
    resources = ["*"]
  }
  statement {
    sid       = "TerminateTaggedWorkers"
    effect    = "Allow"
    actions   = ["ec2:TerminateInstances"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Project"
      values   = ["pneuma-lab"]
    }
  }
}

resource "aws_iam_role_policy" "watcher" {
  name   = "independent-stop-authority"
  role   = aws_iam_role.watcher.id
  policy = data.aws_iam_policy_document.watcher.json
}

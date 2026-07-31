data "aws_iam_policy_document" "controller" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${var.bucket_arn}/${var.bucket_prefix}/*"]
  }
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [var.lease_table_arn]
    condition { test = "ForAllValues:StringEquals" variable = "dynamodb:LeadingKeys" values = [var.lease_key] }
  }
}

data "aws_iam_policy_document" "watcher" {
  statement { effect = "Allow" actions = ["dynamodb:UpdateItem"] resources = [var.lease_table_arn] }
  statement { effect = "Allow" actions = ["ec2:TerminateInstances"] resources = ["*"] }
}

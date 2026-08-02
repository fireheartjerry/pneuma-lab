output "qualification_queue" {
  value = aws_batch_job_queue.qualification.arn
}

output "qualification_job_definition" {
  value = aws_batch_job_definition.worker.arn
}

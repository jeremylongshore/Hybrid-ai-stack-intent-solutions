output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.hybrid_ai_stack.id
}

output "instance_ip" {
  description = "Public IP address"
  value       = var.use_elastic_ip ? aws_eip.hybrid_ai_stack[0].public_ip : aws_instance.hybrid_ai_stack.public_ip
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${var.use_elastic_ip ? aws_eip.hybrid_ai_stack[0].public_ip : aws_instance.hybrid_ai_stack.public_ip}"
}

output "access_urls" {
  description = "Service access URLs"
  value = {
    n8n       = "http://${var.use_elastic_ip ? aws_eip.hybrid_ai_stack[0].public_ip : aws_instance.hybrid_ai_stack.public_ip}:5678"
    api       = "http://${var.use_elastic_ip ? aws_eip.hybrid_ai_stack[0].public_ip : aws_instance.hybrid_ai_stack.public_ip}:8080"
    grafana   = "http://${var.use_elastic_ip ? aws_eip.hybrid_ai_stack[0].public_ip : aws_instance.hybrid_ai_stack.public_ip}:3000"
  }
}

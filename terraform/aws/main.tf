# Hybrid AI Stack - AWS Terraform Configuration
# Deploys a VPS instance with Docker and Ollama pre-configured

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Get latest Ubuntu 22.04 AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

# Security Group
resource "aws_security_group" "hybrid_ai_stack" {
  name_description = "Hybrid AI Stack Security Group"
  description = "Allow SSH, n8n, API Gateway, and monitoring ports"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH"
  }

  ingress {
    from_port   = 5678
    to_port     = 5678
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "n8n"
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "API Gateway"
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Grafana"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "hybrid-ai-stack-sg"
    Project = "hybrid-ai-stack"
    Tier    = var.tier
  }
}

# EC2 Instance
resource "aws_instance" "hybrid_ai_stack" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_types[var.tier]
  
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.hybrid_ai_stack.id]

  root_block_device {
    volume_size = var.disk_sizes[var.tier]
    volume_type = "gp3"
  }

  user_data = <<-EOF
              #!/bin/bash
              set -e
              
              # Update system
              apt-get update -qq
              
              # Install Docker
              curl -fsSL https://get.docker.com | sh
              usermod -aG docker ubuntu
              
              # Install Docker Compose
              apt-get install -y docker-compose
              
              # Install Ollama
              curl -fsSL https://ollama.com/install.sh | sh
              
              # Install Python and dependencies
              apt-get install -y python3-pip python3-venv git
              
              # Clone repository
              cd /home/ubuntu
              git clone https://github.com/jeremylongshore/hybrid-ai-stack.git
              cd hybrid-ai-stack
              
              # Set ownership
              chown -R ubuntu:ubuntu /home/ubuntu/hybrid-ai-stack
              
              # Pull models based on tier
              if [ "${var.tier}" -le 2 ]; then
                sudo -u ubuntu ollama pull tinyllama &
                sudo -u ubuntu ollama pull phi &
              else
                sudo -u ubuntu ollama pull mistral &
              fi
              
              EOF

  tags = {
    Name    = "hybrid-ai-stack-${var.tier}"
    Project = "hybrid-ai-stack"
    Tier    = var.tier
  }
}

# Elastic IP (optional)
resource "aws_eip" "hybrid_ai_stack" {
  count    = var.use_elastic_ip ? 1 : 0
  instance = aws_instance.hybrid_ai_stack.id
  domain   = "vpc"

  tags = {
    Name    = "hybrid-ai-stack-eip"
    Project = "hybrid-ai-stack"
  }
}

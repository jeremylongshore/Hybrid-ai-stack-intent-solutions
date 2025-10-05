variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "tier" {
  description = "Deployment tier (1-4)"
  type        = number
  default     = 2

  validation {
    condition     = var.tier >= 1 && var.tier <= 4
    error_message = "Tier must be between 1 and 4."
  }
}

variable "instance_types" {
  description = "Instance types by tier"
  type        = map(string)
  default = {
    1 = "t3.small"   # 2GB RAM, 2 vCPU
    2 = "t3.large"   # 8GB RAM, 2 vCPU
    3 = "t3.xlarge"  # 16GB RAM, 4 vCPU
    4 = "g5.xlarge"  # GPU instance
  }
}

variable "disk_sizes" {
  description = "Root disk sizes in GB by tier"
  type        = map(number)
  default = {
    1 = 30
    2 = 50
    3 = 100
    4 = 150
  }
}

variable "key_name" {
  description = "SSH key pair name"
  type        = string
}

variable "use_elastic_ip" {
  description = "Allocate Elastic IP"
  type        = bool
  default     = false
}

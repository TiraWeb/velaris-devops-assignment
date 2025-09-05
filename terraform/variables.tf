variable "aws_region" {
  description = "The AWS region to deploy resources in."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "A name for the project to prefix resources."
  type        = string
  default     = "velaris"
}

variable "alert_email" {
  description = "The email address to send SNS alerts to."
  type        = string
  // IMPORTANT: You must change this to your email address.
  default     = "tiranpankaja@gmail.com"
}
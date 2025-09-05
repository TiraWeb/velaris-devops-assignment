resource "aws_ecr_repository" "app" {
  name = "${var.project_name}-app-repo"
  image_tag_mutability = "MUTABLE"
}
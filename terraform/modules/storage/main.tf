# --- S3 Evidence Bucket (created by bootstrap, referenced here) ---

data "aws_s3_bucket" "evidence" {
  bucket = var.s3_bucket_name
}

# No versioning resource needed — bucket is managed by bootstrap

# --- EFS File System (MongoDB Persistence) ---

resource "aws_efs_file_system" "mongodb" {
  encrypted = true

  tags = {
    Name = "${var.project_name}-mongodb-efs"
  }
}

resource "aws_efs_access_point" "mongodb" {
  file_system_id = aws_efs_file_system.mongodb.id

  posix_user {
    uid = 999
    gid = 999
  }

  root_directory {
    path = "/mongodb"
    creation_info {
      owner_uid   = 999
      owner_gid   = 999
      permissions = "755"
    }
  }

  tags = {
    Name = "${var.project_name}-mongodb-efs-ap"
  }
}

resource "aws_security_group" "efs" {
  name        = "${var.project_name}-efs-sg"
  description = "Allow NFS traffic from VPC CIDR"
  vpc_id      = var.vpc_id

  ingress {
    description = "NFS from VPC"
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-efs-sg"
  }
}

resource "aws_efs_mount_target" "mongodb" {
  count           = length(var.private_subnet_ids)
  file_system_id  = aws_efs_file_system.mongodb.id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [aws_security_group.efs.id]
}

# --- Instance Size Mapping ---

locals {
  size_map = {
    small  = { cpu = 512, memory = 1024 }
    medium = { cpu = 1024, memory = 2048 }
    large  = { cpu = 2048, memory = 4096 }
  }

  cpu    = local.size_map[var.instance_size].cpu
  memory = local.size_map[var.instance_size].memory
}

# --- Data Sources ---

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# --- ECR Repository (created by bootstrap, referenced here) ---

data "aws_ecr_repository" "librechat" {
  name = var.project_name
}

# --- CloudWatch Log Group ---

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-ecs-logs"
  }
}

# --- IAM: ECS Task Execution Role ---

resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-task-execution"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_execution_logs" {
  name = "${var.project_name}-ecs-execution-logs"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.ecs.arn}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = "*"
      }
    ]
  })
}

# --- IAM: ECS Task Role (application permissions) ---

resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-task"
  }
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${var.project_name}-s3-write"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "ecs_task_bedrock" {
  name = "${var.project_name}-bedrock-invoke"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/*",
          "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/*"
        ]
      }
    ]
  })
}

# --- ECS Cluster ---

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# --- ECS Task Definition ---

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(local.cpu)
  memory                   = tostring(local.memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "librechat"
      image     = "${data.aws_ecr_repository.librechat.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 3080
          hostPort      = 3080
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "MONGO_URI", value = "mongodb://localhost:27017/librechat" },
        { name = "AWS_DEFAULT_REGION", value = data.aws_region.current.name },
        { name = "BEDROCK_AWS_DEFAULT_REGION", value = "us-east-1" },
        { name = "BEDROCK_AWS_MODELS", value = "us.anthropic.claude-3-5-sonnet-20241022-v2:0,us.anthropic.claude-3-5-haiku-20241022-v1:0,us.amazon.nova-micro-v1:0,us.amazon.nova-lite-v1:0" },
        { name = "CREDS_KEY", value = "f34be427ebb29de8d88c107a71546019685ed8b241d8f2ed00c3df97ad2566f0" },
        { name = "CREDS_IV", value = "e2341419ec3dd3d19b13a1a87fafcbfb" },
        { name = "JWT_SECRET", value = "16f8c0ef4a5d391b26034086c628469d3f9f497f08163ab9b40137092f2909ef" },
        { name = "JWT_REFRESH_SECRET", value = "eaa5191d9c5bc882a3a901c452a1a0d5b51a0e4b5c7e3e2a7e0c1d8f5a6b7c8d" },
        { name = "ALLOW_REGISTRATION", value = "true" },
        { name = "ENDPOINTS", value = "bedrock" }
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "wget -qO- http://localhost:3080/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 120
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "librechat"
        }
      }
    },
    {
      name      = "mongodb"
      image     = "public.ecr.aws/docker/library/mongo:7"
      essential = true
      portMappings = [
        {
          containerPort = 27017
          hostPort      = 27017
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "mongodb"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-task"
  }
}

# --- Application Load Balancer ---

resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids

  tags = {
    Name = "${var.project_name}-alb"
  }
}

resource "aws_lb_target_group" "app" {
  name        = "${var.project_name}-tg"
  port        = 3080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 10
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Name = "${var.project_name}-tg"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }

  tags = {
    Name = "${var.project_name}-http-listener"
  }
}

# --- ECS Service ---

resource "aws_ecs_service" "app" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "librechat"
    container_port   = 3080
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name = "${var.project_name}-service"
  }
}

# --- CloudFront Distribution (provides HTTPS) ---

resource "aws_cloudfront_distribution" "app" {
  enabled         = true
  comment         = "${var.project_name} - HTTPS frontend"
  price_class     = "PriceClass_200"
  is_ipv6_enabled = true

  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = "alb-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "alb-origin"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies {
        forward = "all"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "${var.project_name}-cloudfront"
  }
}

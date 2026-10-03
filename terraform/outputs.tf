# ═══════════════════════════════════════════════════════════════════
# 7. Outputs
# These values need to be placed in your Kubernetes Secrets and .env files
# ═══════════════════════════════════════════════════════════════════

output "cognito_user_pool_id" {
  description = "COGNITO_USER_POOL_ID"
  value       = aws_cognito_user_pool.pool.id
}

output "cognito_client_id" {
  description = "COGNITO_CLIENT_ID"
  value       = aws_cognito_user_pool_client.client.id
}

output "cognito_client_secret" {
  description = "COGNITO_CLIENT_SECRET"
  value       = aws_cognito_user_pool_client.client.client_secret
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3_BUCKET_NAME"
  value       = aws_s3_bucket.product_images.bucket
}

output "eks_cluster_name" {
  description = "EKS Cluster Name"
  value       = module.eks.cluster_name
}

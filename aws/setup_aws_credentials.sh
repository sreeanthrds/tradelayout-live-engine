#!/bin/bash

# Simple helper to connect your AWS account for this project
# 1) Edit the placeholder values below OR rely on `aws configure`
# 2) Run:  chmod +x aws/setup_aws_credentials.sh
# 3) Then: ./aws/setup_aws_credentials.sh

set -e

echo "============================================================="
echo "🔐 AWS Credentials Setup for TradeLayout"
echo "============================================================="
echo ""

# OPTIONAL: hardcode keys here (uncomment & fill IF you want env-based auth)
# WARNING: do NOT commit real keys to Git
#export AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID_HERE"
#export AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY_HERE"
#export AWS_DEFAULT_REGION="ap-south-1"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
  echo "❌ AWS CLI not found. Install it first (macOS):"
  echo "   brew install awscli"
  exit 1
fi

echo "✅ AWS CLI is installed"
echo ""

# If no credentials set in env or config, guide user to aws configure
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "⚠️  No valid AWS credentials detected."
  echo ""
  echo "You have two options:"
  echo "  1) Run: aws configure   (recommended)"
  echo "  2) Edit this file and uncomment/export AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY"
  echo ""
  read -p "Run 'aws configure' now? (y/n): " RUN_CFG
  if [[ "$RUN_CFG" == "y" || "$RUN_CFG" == "Y" ]]; then
    aws configure
  else
    echo "🔁 Skipping aws configure. Make sure env vars are set before running again."
    exit 1
  fi
fi

# Re-check identity
echo ""
echo "🔍 Verifying AWS identity..."
aws sts get-caller-identity || {
  echo "❌ Still no valid AWS credentials. Fix keys and rerun."
  exit 1
}

echo "✅ AWS credentials are valid"

# Optional: test S3 access to tradelayout backup bucket
DEFAULT_BUCKET="tradelayout-backup"
read -p "Test access to S3 bucket '$DEFAULT_BUCKET'? (y/n): " TEST_S3
if [[ "$TEST_S3" == "y" || "$TEST_S3" == "Y" ]]; then
  echo ""
  echo "📦 Listing backups in s3://$DEFAULT_BUCKET/clickhouse-backups/ (if bucket exists)..."
  aws s3 ls "s3://$DEFAULT_BUCKET/clickhouse-backups/" || echo "⚠️  Could not list that path (bucket may not exist or no access)"
fi

echo ""
echo "============================================================="
echo "✅ AWS account is connected for this machine"
echo "You can now run backup/restore scripts that use AWS (S3, EC2, etc.)"
echo "============================================================="

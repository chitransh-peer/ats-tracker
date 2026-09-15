#!/usr/bin/env bash
#
# Provision the ATS Tracker database on Amazon RDS (PostgreSQL 16).
#
# Creates: a DB subnet group, a security group that only the app can reach, and
# the instance itself. Then prints the DATABASE_URL to paste into backend/.env.
#
# This only creates the RDS *instance* and its `ats_tracker` database. The tables
# are created afterwards by Alembic — see 02-init-schema.sh.
#
# Requirements: awscli v2, jq, and credentials with RDS + EC2 permissions.
#
# Usage:
#   export APP_SECURITY_GROUP_ID=sg-0123456789abcdef0   # the EC2 instance's SG
#   ./01-create-database.sh
#
# Safe to re-run: every step checks for an existing resource first.

set -euo pipefail

# ---------------------------------------------------------------- configuration
AWS_REGION="${AWS_REGION:-ap-south-1}"
DB_IDENTIFIER="${DB_IDENTIFIER:-ats-tracker-db}"
DB_NAME="${DB_NAME:-ats_tracker}"
DB_USERNAME="${DB_USERNAME:-ats_admin}"
DB_INSTANCE_CLASS="${DB_INSTANCE_CLASS:-db.t4g.micro}"
DB_ENGINE_VERSION="${DB_ENGINE_VERSION:-16}"
DB_STORAGE_GB="${DB_STORAGE_GB:-20}"
DB_BACKUP_RETENTION_DAYS="${DB_BACKUP_RETENTION_DAYS:-14}"
DB_SECURITY_GROUP_NAME="${DB_SECURITY_GROUP_NAME:-ats-db-sg}"
DB_SUBNET_GROUP_NAME="${DB_SUBNET_GROUP_NAME:-ats-db-subnet-group}"

# Security group of the EC2 instance running the app. Required: it is the only
# source allowed to reach port 5432.
APP_SECURITY_GROUP_ID="${APP_SECURITY_GROUP_ID:-}"

# ---------------------------------------------------------------------- helpers
info() { printf '\033[0;36m==>\033[0m %s\n' "$*"; }
ok() { printf '\033[0;32m  ok\033[0m %s\n' "$*"; }
warn() { printf '\033[0;33m  !!\033[0m %s\n' "$*" >&2; }
die() {
  printf '\033[0;31mERROR\033[0m %s\n' "$*" >&2
  exit 1
}

aws_q() { aws --region "$AWS_REGION" --output text "$@"; }

# ------------------------------------------------------------------- preflight
command -v aws >/dev/null || die "awscli not found."
command -v jq >/dev/null || die "jq not found."

aws sts get-caller-identity >/dev/null 2>&1 \
  || die "AWS credentials are not configured or have expired."

[[ -n "$APP_SECURITY_GROUP_ID" ]] \
  || die "APP_SECURITY_GROUP_ID is required. Set it to the EC2 instance's security group id."

info "Region ................ $AWS_REGION"
info "Instance identifier ... $DB_IDENTIFIER"
info "Instance class ........ $DB_INSTANCE_CLASS"
info "Database name ......... $DB_NAME"
echo

# ------------------------------------------------------------------------- VPC
info "Resolving the default VPC"
VPC_ID="$(aws_q ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId')"
[[ "$VPC_ID" != "None" && -n "$VPC_ID" ]] \
  || die "No default VPC found. Set VPC_ID and SUBNET_IDS manually for a custom VPC."
ok "VPC $VPC_ID"

# --------------------------------------------------------------- subnet group
# RDS requires subnets in at least two availability zones, even single-AZ.
if aws_q rds describe-db-subnet-groups --db-subnet-group-name "$DB_SUBNET_GROUP_NAME" >/dev/null 2>&1; then
  ok "Subnet group $DB_SUBNET_GROUP_NAME already exists"
else
  info "Creating subnet group $DB_SUBNET_GROUP_NAME"
  mapfile -t SUBNET_IDS < <(aws_q ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[].SubnetId' | tr '\t' '\n')

  [[ "${#SUBNET_IDS[@]}" -ge 2 ]] \
    || die "Need at least 2 subnets in different AZs; found ${#SUBNET_IDS[@]}."

  aws --region "$AWS_REGION" rds create-db-subnet-group \
    --db-subnet-group-name "$DB_SUBNET_GROUP_NAME" \
    --db-subnet-group-description "ATS Tracker database subnets" \
    --subnet-ids "${SUBNET_IDS[@]}" >/dev/null
  ok "Created with ${#SUBNET_IDS[@]} subnets"
fi

# ------------------------------------------------------------- security group
DB_SG_ID="$(aws_q ec2 describe-security-groups \
  --filters "Name=group-name,Values=$DB_SECURITY_GROUP_NAME" "Name=vpc-id,Values=$VPC_ID" \
  --query 'SecurityGroups[0].GroupId' 2>/dev/null || echo "None")"

if [[ "$DB_SG_ID" == "None" || -z "$DB_SG_ID" ]]; then
  info "Creating security group $DB_SECURITY_GROUP_NAME"
  DB_SG_ID="$(aws_q ec2 create-security-group \
    --group-name "$DB_SECURITY_GROUP_NAME" \
    --description "ATS Tracker RDS - reachable only from the application" \
    --vpc-id "$VPC_ID" \
    --query 'GroupId')"
  ok "Created $DB_SG_ID"
else
  ok "Security group $DB_SG_ID already exists"
fi

# Source is the app's security group, never a CIDR. The database must never be
# reachable from the internet.
info "Authorising 5432 from $APP_SECURITY_GROUP_ID only"
if aws --region "$AWS_REGION" ec2 authorize-security-group-ingress \
  --group-id "$DB_SG_ID" \
  --protocol tcp --port 5432 \
  --source-group "$APP_SECURITY_GROUP_ID" >/dev/null 2>&1; then
  ok "Ingress rule added"
else
  ok "Ingress rule already present"
fi

# ------------------------------------------------------------------- password
# Generated here so it never has to be typed or shared over chat.
DB_PASSWORD="$(aws_q secretsmanager get-random-password \
  --password-length 32 --exclude-punctuation --require-each-included-type \
  --query 'RandomPassword' 2>/dev/null || openssl rand -base64 24 | tr -d '/+=')"

# --------------------------------------------------------------- the instance
if aws_q rds describe-db-instances --db-instance-identifier "$DB_IDENTIFIER" >/dev/null 2>&1; then
  warn "Instance $DB_IDENTIFIER already exists — not modifying it."
  warn "The password below was NOT applied. Use your stored password."
  DB_PASSWORD="<your existing password>"
else
  info "Creating RDS instance (this typically takes 5-10 minutes)"
  aws --region "$AWS_REGION" rds create-db-instance \
    --db-instance-identifier "$DB_IDENTIFIER" \
    --db-name "$DB_NAME" \
    --engine postgres \
    --engine-version "$DB_ENGINE_VERSION" \
    --db-instance-class "$DB_INSTANCE_CLASS" \
    --allocated-storage "$DB_STORAGE_GB" \
    --storage-type gp3 \
    --storage-encrypted \
    --master-username "$DB_USERNAME" \
    --master-user-password "$DB_PASSWORD" \
    --vpc-security-group-ids "$DB_SG_ID" \
    --db-subnet-group-name "$DB_SUBNET_GROUP_NAME" \
    --backup-retention-period "$DB_BACKUP_RETENTION_DAYS" \
    --preferred-backup-window "18:00-19:00" \
    --preferred-maintenance-window "sun:19:30-sun:20:30" \
    --no-publicly-accessible \
    --no-multi-az \
    --auto-minor-version-upgrade \
    --copy-tags-to-snapshot \
    --deletion-protection \
    --enable-performance-insights \
    --tags "Key=Project,Value=ats-tracker" "Key=ManagedBy,Value=01-create-database.sh" \
    >/dev/null
  ok "Create requested"

  info "Waiting for the instance to become available"
  aws --region "$AWS_REGION" rds wait db-instance-available \
    --db-instance-identifier "$DB_IDENTIFIER"
  ok "Instance is available"
fi

# --------------------------------------------------------------------- output
DB_ENDPOINT="$(aws_q rds describe-db-instances \
  --db-instance-identifier "$DB_IDENTIFIER" \
  --query 'DBInstances[0].Endpoint.Address')"

cat <<REPORT

────────────────────────────────────────────────────────────────────────
 Database ready
────────────────────────────────────────────────────────────────────────

 Endpoint   : $DB_ENDPOINT
 Database   : $DB_NAME
 Username   : $DB_USERNAME
 Password   : $DB_PASSWORD
 Backups    : automated, ${DB_BACKUP_RETENTION_DAYS}-day retention
 Encryption : at rest, enabled
 Access     : private; only $APP_SECURITY_GROUP_ID can reach port 5432

 Put this in backend/.env:

   DATABASE_URL=postgresql+psycopg://$DB_USERNAME:$DB_PASSWORD@$DB_ENDPOINT:5432/$DB_NAME

 The 'postgresql+psycopg://' prefix is required — this app uses psycopg 3.
 A plain 'postgres://' URL will fail to connect.

 Store the password in Secrets Manager or your password manager now. It is
 not recoverable from AWS afterwards.

 Next: ./02-init-schema.sh   (creates the tables and the first admin user)
────────────────────────────────────────────────────────────────────────

REPORT

To run `platform-cli` on an EC2 instance (e.g., for testing or automation):

#1. Launch EC2 Instance

- Launch an Amazon Linux 2 or Ubuntu EC2 instance.
- Make sure it has:
  - IAM role attached with necessary permissions.
  - Inbound SSH access (for setup, if needed).
  - Python 3.8+ installed (or install it manually).
  - pip
  - AWS CLI

# 2. SSH Into the Instance

```bash
ssh -i <your-key.pem> ec2-user@<ec2-public-ip

git clone <url-of-your-repo>
cd platform-cli

#install updates
sudo yum update -y  # (or apt-get update)
pip3 install -r requirements.txt
pip3 install -r dev-requirements.txt
sudo yum install python3-pip -y  # For Amazon Linux

#login
aws configure


# platform-cli

A command-line tool (CLI) for managing AWS resources including EC2, S3, and Route53.
Designed for developer use, with built-in security constraints and guardrails.


# Features

-  Create, start, stop, and list EC2 instances
  (with a built-in limit: max 2 running at once)
-  Manage S3 buckets with public/private access control
-  Manage DNS records within Route53 hosted zones
-  All resources are auto-tagged:
  - `CreatedBy=platform-cli`
  - `Owner=<your-username>`


# Prerequisites

- Python 3.8 or higher
- AWS CLI installed and configured (`aws configure` or named profile)
- Valid AWS IAM permissions:
  - EC2 (manage instances)
  - S3 (create/manage buckets)
  - Route53 (read/write DNS records)
  - SSM (optional: for session manager or parameter store)
  
#you can use the next script as a bash file inorder to install the requirememts
# name: setup-platform-cli.sh

set -e

echo " Updating system..."
sudo yum update -y

echo " Installing dependencies: git, Python 3, pip..."
sudo yum install -y git python3-pip
pip3 install --upgrade pip

echo " Cloning platform-cli repository..."

# enter you repo
GIT_REPO="<url-of-your-repo>"
git clone "$GIT_REPO"
cd platform-cli

echo " Installing Python dependencies..."
pip3 install -r requirements.txt
pip3 install -r dev-requirements.txt

echo " Platform CLI ready to use."
echo " Don't forget to run 'aws configure' before using the CLI

# Run unit tests
pytest


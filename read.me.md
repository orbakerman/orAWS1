# platform-cli

A command-line tool (CLI) for managing AWS resources including EC2, S3, and Route53.
Designed for developer use, with built-in security constraints and guardrails.

---

# Features

-  Create, start, stop, and list EC2 instances
  (with a built-in limit: max 2 running at once)
-  Manage S3 buckets with public/private access control
-  Manage DNS records within Route53 hosted zones
-  All resources are auto-tagged:
  - `CreatedBy=platform-cli`
  - `Owner=<your-username>`

---

##  Prerequisites

- Python 3.8 or higher
- AWS CLI installed and configured (`aws configure` or named profile)
- Valid AWS IAM permissions:
  - EC2 (manage instances)
  - S3 (create/manage buckets)
  - Route53 (read/write DNS records)
  - SSM (optional: for session manager or parameter store)

---

## ⚙ Installation

```bash
git clone <url-of-your-repo>
cd platform-cli
pip install -r requirements.txt

# Install dev dependencies
pip install -r dev-requirements.txt

# Run unit tests
pytest


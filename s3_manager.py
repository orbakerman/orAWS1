# s3_manager.py
import os, json
import boto3
from botocore.exceptions import ClientError
import click

# ---- session/region ----
_session = boto3.session.Session()
_region = _session.region_name or os.getenv("AWS_REGION") or "us-east-1"

s3 = boto3.client("s3", region_name=_region)
s3_resource = boto3.resource("s3", region_name=_region)

# ========== Core Logic (כפי שהיה, עם תיקונים קטנים) ==========
def handle_s3(action, params):
    if action == "create":
        create_bucket(params)
    elif action == "upload":
        upload_file(params)
    elif action == "list":
        list_buckets()
    else:
        print(f"error: unsupported action: {action}")

def create_bucket(params):
    bucket_name = params.get("name")
    visibility = params.get("visibility", "private")
    username = os.getenv("USER") or os.getenv("USERNAME") or "unknown"

    if not bucket_name:
        print("error: must input --params name=<bucket-name>")
        return

    if visibility not in ["private", "public"]:
        print("error: visibility must be 'private' or 'public'")
        return

    if visibility == "public":
        confirm = params.get("yes") or input("are you sure you want to create a public bucket? (yes/no): ")
        if str(confirm).lower() != "yes":
            print("aborted.")
            return

    try:
        # region handling: ל-us-east-1 אין CreateBucketConfiguration
        kwargs = dict(Bucket=bucket_name)
        if _region != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": _region}

        s3.create_bucket(**kwargs)

        # tags
        tagging = s3_resource.BucketTagging(bucket_name)
        tagging.put(Tagging={"TagSet": [
            {"Key": "CreatedBy", "Value": "platform-cli"},
            {"Key": "Owner", "Value": username}
        ]})

        # public policy (optional)
        if visibility == "public":
            policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                }]
            }
            s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))

        print(f"bucket created: {bucket_name}")

    except ClientError as e:
        print(f"error creating bucket: {e}")

def upload_file(params):
    bucket = params.get("bucket")
    file_path = params.get("file")

    if not bucket or not file_path:
        print("error: must input: --params bucket=<name> file=<path>")
        return

    if not is_cli_bucket(bucket):
        print("error: can only upload to buckets created by platform-cli.")
        return

    file_name = os.path.basename(file_path)
    try:
        s3.upload_file(file_path, bucket, file_name)
        print(f"file uploaded: {file_name} → {bucket}")
    except ClientError as e:
        print(f"error uploading file: {e}")

def list_buckets():
    try:
        buckets = s3.list_buckets()
        for b in buckets.get("Buckets", []):
            name = b["Name"]
            tags = get_bucket_tags(name)
            if tags.get("CreatedBy") == "platform-cli":
                print(f"🪣 {name}")
    except ClientError as e:
        print(f"error listing buckets: {e}")

def get_bucket_tags(bucket_name):
    try:
        tagging = s3.get_bucket_tagging(Bucket=bucket_name)
        return {t["Key"]: t["Value"] for t in tagging.get("TagSet", [])}
    except Exception:
        return {}

def is_cli_bucket(bucket_name):
    tags = get_bucket_tags(bucket_name)
    return tags.get("CreatedBy") == "platform-cli"

# ========== Click Group (מה שחסר ל-cli.py) ==========
@click.group(name="s3")
def s3_group():
    """Manage S3 buckets"""

@s3_group.command("create-bucket")
@click.option("--name", required=True, help="Bucket name (must be globally unique)")
@click.option("--visibility", type=click.Choice(["private", "public"]), default="private")
@click.option("--yes", is_flag=True, help="Auto-confirm public bucket prompt")
def _create_bucket_cmd(name, visibility, yes):
    create_bucket({"name": name, "visibility": visibility, "yes": "yes" if yes else None})

@s3_group.command("upload-file")
@click.option("--bucket", required=True)
@click.option("--file", "file_", required=True, type=click.Path(exists=True))
def _upload_file_cmd(bucket, file_):
    upload_file({"bucket": bucket, "file": file_})

@s3_group.command("list")
def _list_cmd():
    list_buckets()

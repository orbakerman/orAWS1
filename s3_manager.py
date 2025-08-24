import boto3
import os
import sys
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
s3_resource = boto3.resource('s3')

def handle_s3(action, params):
    if action == 'create':
        create_bucket(params)
    elif action == 'upload':
        upload_file(params)
    elif action == 'list':
        list_buckets()
    else:
        print(f"error: could not spourt action: {action}")

def create_bucket(params):
    bucket_name = params.get('name')
    visibility = params.get('visibility', 'private')
    region = boto3.session.Session().region_name
    username = os.getenv("USER") or os.getenv("USERNAME") or "unknown"

    if not bucket_name:
        print("error: must input --params name=<bucket-name>")
        return

    if visibility not in ['private', 'public']:
        print("error: visibility must be  'private' or 'public'")
        return

    if visibility == 'public':
        confirm = input("are you sure you want to create a public bucket? (yes/no): ")
        if confirm.lower() != 'yes':
            print("undo.")
            return

    try:
        # creating buckets
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )

        # tags
        tagging = s3_resource.BucketTagging(bucket_name)
        tagging.put(Tagging={
            'TagSet': [
                {'Key': 'CreatedBy', 'Value': 'platform-cli'},
                {'Key': 'Owner', 'Value': username}
            ]
        })

        #  public policy
        if visibility == 'public':
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
        print(f"error making bucket: {e}")

def upload_file(params):
    bucket = params.get('bucket')
    file_path = params.get('file')

    if not bucket or not file_path:
        print("error: must input: --params bucket=<name> file=<path>")
        return

    # check if the bucket was created using CLI
    if not is_cli_bucket(bucket):
        print("error: can only upload what was created in CLI.")
        return

    file_name = os.path.basename(file_path)

    try:
        s3.upload_file(file_path, bucket, file_name)
        print(f"✅ file uploaded: {file_name} → {bucket}")
    except ClientError as e:
        print(f"error uploading files: {e}")

def list_buckets():
    try:
        buckets = s3.list_buckets()
        for b in buckets['Buckets']:
            name = b['Name']
            tags = get_bucket_tags(name)
            if tags.get('CreatedBy') == 'platform-cli':
                print(f"🪣 {name}")
    except ClientError as e:
        print(f"error could not find the buckets list: {e}")

def get_bucket_tags(bucket_name):
    try:
        tagging = s3.get_bucket_tagging(Bucket=bucket_name)
        return {tag['Key']: tag['Value'] for tag in tagging['TagSet']}
    except:
        return {}

def is_cli_bucket(bucket_name):
    tags = get_bucket_tags(bucket_name)
    return tags.get('CreatedBy') == 'platform-cli'


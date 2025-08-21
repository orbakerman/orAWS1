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
        print(f"שגיאה: פעולה לא נתמכת: {action}")

def create_bucket(params):
    bucket_name = params.get('name')
    visibility = params.get('visibility', 'private')
    region = boto3.session.Session().region_name
    username = os.getenv("USER") or os.getenv("USERNAME") or "unknown"

    if not bucket_name:
        print("שגיאה: יש לציין --params name=<bucket-name>")
        return

    if visibility not in ['private', 'public']:
        print("שגיאה: visibility חייב להיות 'private' או 'public'")
        return

    if visibility == 'public':
        confirm = input("אתה בטוח שברצונך ליצור דלי ציבורי? (yes/no): ")
        if confirm.lower() != 'yes':
            print("בוטל.")
            return

    try:
        # יצירת הדלי
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )

        # תיוג
        tagging = s3_resource.BucketTagging(bucket_name)
        tagging.put(Tagging={
            'TagSet': [
                {'Key': 'CreatedBy', 'Value': 'platform-cli'},
                {'Key': 'Owner', 'Value': username}
            ]
        })

        # הגדרת public policy אם רלוונטי
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

        print(f"דלי נוצר בהצלחה: {bucket_name}")

    except ClientError as e:
        print(f"שגיאה ביצירת דלי: {e}")

def upload_file(params):
    bucket = params.get('bucket')
    file_path = params.get('file')

    if not bucket or not file_path:
        print("שגיאה: יש לציין --params bucket=<name> file=<path>")
        return

    # בדוק אם הדלי הוא CLI
    if not is_cli_bucket(bucket):
        print("שגיאה: ניתן להעלות קבצים רק לדליים שנוצרו על ידי CLI.")
        return

    file_name = os.path.basename(file_path)

    try:
        s3.upload_file(file_path, bucket, file_name)
        print(f"✅ הקובץ הועלה: {file_name} → {bucket}")
    except ClientError as e:
        print(f"שגיאה בהעלאת קובץ: {e}")

def list_buckets():
    try:
        buckets = s3.list_buckets()
        for b in buckets['Buckets']:
            name = b['Name']
            tags = get_bucket_tags(name)
            if tags.get('CreatedBy') == 'platform-cli':
                print(f"🪣 {name}")
    except ClientError as e:
        print(f"שגיאה בשליפת רשימת דליים: {e}")

def get_bucket_tags(bucket_name):
    try:
        tagging = s3.get_bucket_tagging(Bucket=bucket_name)
        return {tag['Key']: tag['Value'] for tag in tagging['TagSet']}
    except:
        return {}

def is_cli_bucket(bucket_name):
    tags = get_bucket_tags(bucket_name)
    return tags.get('CreatedBy') == 'platform-cli'


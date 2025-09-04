# cleanup.py
import os
import boto3
from botocore.exceptions import ClientError

TAG_CREATEDBY_KEY = "CreatedBy"
TAG_CREATEDBY_VAL = "platform-cli"
TAG_OWNER_KEY = "Owner"

def _default_owner():
    return os.getenv("USER") or os.getenv("USERNAME") or "unknown"

def cleanup_resources(
    dry_run=False,
    owner=None,
    only=None,                 # iterable: {"ec2","s3","route53"}
    instance_ids=None,         # iterable of EC2 instance IDs to delete explicitly
    name_prefix=None,          # prefix to match EC2 Name tag / S3 bucket / Zone name
    bucket_names=None,         # iterable of bucket names
    zone_ids=None              # iterable of hosted zone IDs (Z...)
):
    owner = owner or _default_owner()
    only = set(only or ["ec2", "s3", "route53"])
    print(f"=== cleanup platform-cli (owner={owner}, dry_run={dry_run}, only={','.join(sorted(only))}) ===")
    if "ec2" in only:
        cleanup_ec2(dry_run, owner, instance_ids, name_prefix)
    if "s3" in only:
        cleanup_s3(dry_run, owner, bucket_names, name_prefix)
    if "route53" in only:
        cleanup_route53(dry_run, owner, zone_ids, name_prefix)
    print("=== done ===")

# ---------- EC2 ----------
def cleanup_ec2(dry_run, owner, instance_ids, name_prefix):
    ec2r = boto3.resource("ec2")
    ec2 = boto3.client("ec2")

    # בסיס: CreatedBy & Owner
    filters = [
        {"Name": f"tag:{TAG_CREATEDBY_KEY}", "Values": [TAG_CREATEDBY_VAL]},
        {"Name": f"tag:{TAG_OWNER_KEY}", "Values": [owner]},
    ]
    if name_prefix:
        filters.append({"Name": "tag:Name", "Values": [f"{name_prefix}*"]})

    # אם נתנו IDs ספציפיים – נשתמש בהם, אבל עדיין נוודא תגיות
    ids = []
    if instance_ids:
        # סנן רק כאלה שבאמת נוצרו ע"י הכלי ושייכים ל-owner
        desc = ec2.describe_instances(InstanceIds=list(instance_ids))
        for r in desc.get("Reservations", []):
            for i in r.get("Instances", []):
                tags = {t["Key"]: t["Value"] for t in i.get("Tags", [])}
                if tags.get(TAG_CREATEDBY_KEY) == TAG_CREATEDBY_VAL and tags.get(TAG_OWNER_KEY) == owner:
                    ids.append(i["InstanceId"])
    else:
        ids = [i.id for i in ec2r.instances.filter(Filters=filters)]

    if not ids:
        print("EC2: nothing to delete.")
        return

    print(f"EC2: terminating {ids}")
    if dry_run:
        return
    try:
        ec2r.instances.filter(InstanceIds=ids).terminate()
    except ClientError as e:
        print(f"EC2: error terminating: {e}")

# ---------- S3 ----------
def cleanup_s3(dry_run, owner, bucket_names, name_prefix):
    s3 = boto3.client("s3")
    s3r = boto3.resource("s3")
    resp = s3.list_buckets()

    targets = set(bucket_names or [])
    for b in resp.get("Buckets", []):
        name = b["Name"]
        if name_prefix and not name.startswith(name_prefix):
            # אם יש לנו רשימה מפורשת של שמות, נבדוק אותה בהמשך
            if name not in targets:
                continue
        try:
            t = s3.get_bucket_tagging(Bucket=name)
            tags = {x["Key"]: x["Value"] for x in t.get("TagSet", [])}
        except ClientError:
            continue
        if tags.get(TAG_CREATEDBY_KEY) != TAG_CREATEDBY_VAL or tags.get(TAG_OWNER_KEY) != owner:
            continue
        if bucket_names and name not in targets:
            continue

        print(f"S3: deleting bucket {name}")
        if dry_run:
            continue
        bucket = s3r.Bucket(name)
        try:
            bucket.object_versions.all().delete()
        except ClientError:
            pass
        try:
            bucket.objects.all().delete()
        except ClientError:
            pass
        try:
            bucket.delete()
        except ClientError as e:
            print(f"S3: error deleting bucket {name}: {e}")

# ---------- Route53 ----------
def cleanup_route53(dry_run, owner, zone_ids, name_prefix):
    r53 = boto3.client("route53")
    try:
        zones = r53.list_hosted_zones()["HostedZones"]
    except ClientError as e:
        print(f"Route53: list_hosted_zones error: {e}")
        return

    wanted_ids = set(zone_ids or [])
    for z in zones:
        zid = z["Id"].split("/")[-1]
        zname = z["Name"].rstrip(".")
        if name_prefix and not zname.startswith(name_prefix):
            if zone_ids and zid not in wanted_ids:
                continue
        try:
            tagres = r53.list_tags_for_resource(ResourceType="hostedzone", ResourceId=zid)
            tags = {t["Key"]: t["Value"] for t in tagres["ResourceTagSet"].get("Tags", [])}
        except ClientError:
            continue
        if tags.get(TAG_CREATEDBY_KEY) != TAG_CREATEDBY_VAL or tags.get(TAG_OWNER_KEY) != owner:
            continue
        if zone_ids and zid not in wanted_ids:
            continue

        print(f"Route53: purge records and delete zone {zname} ({zid})")
        if dry_run:
            continue

        # מחיקת רשומות שאינן NS/SOA במנות
        try:
            rrsets = r53.list_resource_record_sets(HostedZoneId=zid)["ResourceRecordSets"]
        except ClientError as e:
            print(f"Route53: list RR error for {zid}: {e}")
            continue

        changes = []
        for rr in rrsets:
            if rr["Type"] in ("NS", "SOA"):
                continue
            change = {"Action": "DELETE", "ResourceRecordSet": {"Name": rr["Name"], "Type": rr["Type"]}}
            if "AliasTarget" in rr:
                change["ResourceRecordSet"]["AliasTarget"] = rr["AliasTarget"]
            else:
                change["ResourceRecordSet"]["TTL"] = rr["TTL"]
                change["ResourceRecordSet"]["ResourceRecords"] = rr.get("ResourceRecords", [])
            changes.append(change)

        for i in range(0, len(changes), 90):
            batch = changes[i:i+90]
            try:
                r53.change_resource_record_sets(HostedZoneId=zid, ChangeBatch={"Changes": batch})
            except ClientError as e:
                print(f"Route53: change batch error in {zid}: {e}")

        try:
            r53.delete_hosted_zone(Id=zid)
        except ClientError as e:
            print(f"Route53: delete zone error {zid}: {e}")

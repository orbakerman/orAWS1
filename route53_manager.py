# route53_manager.py
import os, time, uuid, click, boto3
from botocore.exceptions import ClientError

# Route53 הוא שירות גלובלי (בלי region); ל-VPC נשתמש ב-region הדיפולטי שלך
_session = boto3.session.Session()
_DEFAULT_REGION = _session.region_name or os.getenv("AWS_REGION") or "us-east-1"
r53 = boto3.client("route53")
ec2 = boto3.client("ec2", region_name=_DEFAULT_REGION)

def _username():
    return os.getenv("USER") or os.getenv("USERNAME") or "unknown"

def _strip_zone_id(zid: str) -> str:
    return zid.split("/")[-1]

def _tag_zone(zone_id: str):
    try:
        r53.change_tags_for_resource(
            ResourceType="hostedzone",
            ResourceId=zone_id,
            AddTags=[
                {"Key": "CreatedBy", "Value": "platform-cli"},
                {"Key": "Owner", "Value": _username()},
            ],
        )
    except ClientError:
        pass

@click.group(name="route53")
def route53_group():
    """Manage Route53 records & zones"""

@route53_group.command("list-zones")
def list_zones():
    """List hosted zones"""
    try:
        paginator = r53.get_paginator("list_hosted_zones")
        for page in paginator.paginate():
            for z in page.get("HostedZones", []):
                name = z["Name"]
                zone_id = _strip_zone_id(z["Id"])
                private = z.get("Config", {}).get("PrivateZone")
                click.echo(f"{name}\t{zone_id}\t{'private' if private else 'public'}")
    except ClientError as e:
        click.echo(f"error listing zones: {e}", err=True)

@route53_group.command("create-zone")
@click.option("--name", required=True, help="Domain name (e.g. example.com)")
@click.option("--private", is_flag=True, help="Create a private hosted zone")
@click.option("--vpc-id", default=None, help="VPC ID for private zone (if omitted, uses default VPC)")
@click.option("--vpc-region", default=_DEFAULT_REGION, show_default=True, help="VPC region for private zone")
def create_zone(name, private, vpc_id, vpc_region):
    """
    Create a hosted zone (public by default).
    For private zones, requires a VPC (auto-picks default VPC if not provided).
    """
    if private:
        if not vpc_id:
            # נסה לאתר VPC דיפולטי
            vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}]).get("Vpcs", [])
            if not vpcs:
                raise click.ClickException("no default VPC found; pass --vpc-id")
            vpc_id = vpcs[0]["VpcId"]

    try:
        kwargs = {
            "Name": name.rstrip("."),
            "CallerReference": f"platform-cli-{time.time()}-{uuid.uuid4()}",
            "HostedZoneConfig": {"Comment": "platform-cli", "PrivateZone": bool(private)},
        }
        if private:
            kwargs["VPC"] = {"VPCRegion": vpc_region, "VPCId": vpc_id}

        resp = r53.create_hosted_zone(**kwargs)
        zone_id = _strip_zone_id(resp["HostedZone"]["Id"])
        _tag_zone(zone_id)

        click.echo(f"hosted zone created: {name}  id={zone_id}  {'private' if private else 'public'}")

        if not private:
            # הצג NS לרישום ב-Registrar
            rrs = r53.list_resource_record_sets(HostedZoneId=zone_id)["ResourceRecordSets"]
            ns = next((rr for rr in rrs if rr["Type"] == "NS" and rr["Name"].rstrip(".") == name.rstrip(".")), None)
            if ns:
                ns_vals = ", ".join(sorted(v["Value"] for v in ns.get("ResourceRecords", [])))
                click.echo(f"nameservers: {ns_vals}")
            click.echo("Remember: update your domain's registrar to use these Route53 nameservers.")
    except ClientError as e:
        click.echo(f"error creating hosted zone: {e}", err=True)

@route53_group.command("upsert")
@click.option("--zone-id", required=True, help="HostedZoneId (e.g. Z123...)")
@click.option("--record", required=True, help="Record name (e.g. test.example.com)")
@click.option("--type", "rtype", required=True, help="A|AAAA|CNAME|TXT|MX|...")
@click.option("--value", required=True, help="Value (e.g. 1.2.3.4 or target.domain)")
@click.option("--ttl", default=60, show_default=True, type=int)
def upsert_record(zone_id, record, rtype, value, ttl):
    """Create/Update (UPSERT) a DNS record"""
    try:
        r53.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                "Comment": "platform-cli",
                "Changes": [{
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": record.rstrip("."),
                        "Type": rtype,
                        "TTL": ttl,
                        "ResourceRecords": [{"Value": value}],
                    }
                }]
            }
        )
        click.echo("record upserted")
    except ClientError as e:
        click.echo(f"error upserting record: {e}", err=True)

@route53_group.command("delete-zone")
@click.option("--zone-id", required=True, help="HostedZoneId (Z...)")
@click.option("--force", is_flag=True, help="Delete all non NS/SOA records first")
def delete_zone(zone_id, force):
    """Delete a hosted zone (optionally purge records first)"""
    zone_id = _strip_zone_id(zone_id)
    try:
        if force:
            _purge_non_default_records(zone_id)
        # וודא שלא נשארו רשומות שאינן NS/SOA
        leftover = _list_non_default_records(zone_id)
        if leftover:
            click.echo("zone still has non-default records; use --force or delete them first:", err=True)
            for rr in leftover:
                click.echo(f" - {rr['Name']} {rr['Type']}")
            raise SystemExit(2)
        r53.delete_hosted_zone(Id=zone_id)
        click.echo("hosted zone deleted")
    except ClientError as e:
        click.echo(f"error deleting hosted zone: {e}", err=True)

def _list_non_default_records(zone_id):
    rrs = r53.list_resource_record_sets(HostedZoneId=zone_id)["ResourceRecordSets"]
    return [rr for rr in rrs if rr["Type"] not in ("NS", "SOA")]

def _purge_non_default_records(zone_id):
    # מחיקה בקבוצות של עד 100 שינויים
    batch = []
    for rr in _list_non_default_records(zone_id):
        change = {"Action": "DELETE", "ResourceRecordSet": {"Name": rr["Name"], "Type": rr["Type"]}}
        if "AliasTarget" in rr:
            change["ResourceRecordSet"]["AliasTarget"] = rr["AliasTarget"]
        else:
            change["ResourceRecordSet"]["TTL"] = rr["TTL"]
            change["ResourceRecordSet"]["ResourceRecords"] = rr["ResourceRecords"]
        batch.append(change)
        if len(batch) == 90:  # שוליים לבטיחות
            r53.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch={"Changes": batch})
            batch = []
    if batch:
        r53.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch={"Changes": batch})

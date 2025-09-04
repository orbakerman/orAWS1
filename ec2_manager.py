# ec2_manager.py
import os
import click
import boto3
from botocore.exceptions import ClientError

# ---- session/region ----
_session = boto3.session.Session()
_region = _session.region_name or os.getenv("AWS_REGION") or "us-east-1"
ec2 = boto3.client("ec2", region_name=_region)
ssm = boto3.client("ssm", region_name=_region)

ALLOWED_TYPES = {"t3.micro", "t2.small"}
MAX_RUNNING = 2  # guardrail

def _username():
    return os.getenv("USER") or os.getenv("USERNAME") or "unknown"

def _count_running_cli_instances():
    resp = ec2.describe_instances(
        Filters=[
            {"Name": "instance-state-name", "Values": ["running", "pending"]},
            {"Name": "tag:CreatedBy", "Values": ["platform-cli"]},
        ]
    )
    return sum(len(r["Instances"]) for r in resp.get("Reservations", []))

def _ensure_cli_instance(iid: str):
    res = ec2.describe_instances(InstanceIds=[iid])
    inst = res["Reservations"][0]["Instances"][0]
    tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
    if tags.get("CreatedBy") != "platform-cli":
        click.echo("refusing: instance was not created by platform-cli", err=True)
        raise SystemExit(2)
    return inst

def _resolve_ami(ami: str):
    """Return AMI ID. Supports literals (ami-xxxx), 'amazon-linux', 'ubuntu' via SSM."""
    if ami.startswith("ami-"):
        return ami
    names = []
    if ami == "amazon-linux":
        names = [
            "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64",
            "/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2",
        ]
    elif ami == "ubuntu":
        names = [
            "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id",
            "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id",
        ]
    for name in names:
        try:
            return ssm.get_parameter(Name=name)["Parameter"]["Value"]
        except ClientError:
            continue
    raise click.ClickException("could not resolve AMI; pass --ami ami-xxxxxxxx or use 'amazon-linux'/'ubuntu'")

@click.group(name="ec2")
def ec2_group():
    """Manage EC2 instances created by platform-cli"""

@ec2_group.command("create")
@click.option("--name", required=True, help="Name tag")
@click.option("--ami", default="amazon-linux", show_default=True,
              help="amazon-linux | ubuntu | ami-xxxxxxxxxxxxxxxxx")
@click.option("--instance-type", type=click.Choice(sorted(ALLOWED_TYPES)),
              default="t3.micro", show_default=True)
@click.option("--key-name", default=None, help="EC2 key pair name")
@click.option("--sg-id", multiple=True, help="SecurityGroupIds (sg-...) — can repeat")
@click.option("--subnet-id", default=None, help="SubnetId (optional)")
def create_instance(name, ami, instance_type, key_name, sg_id, subnet_id):
    """Create a new EC2 instance (guardrail: max 2 running/pending)"""
    running = _count_running_cli_instances()
    if running >= MAX_RUNNING:
        raise click.ClickException(f"guardrail: you already have {running} running/pending (max={MAX_RUNNING})")

    ami_id = _resolve_ami(ami)

    try:
        kwargs = {
            "ImageId": ami_id,
            "InstanceType": instance_type,
            "MinCount": 1, "MaxCount": 1,
            "TagSpecifications": [{
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": name},
                    {"Key": "CreatedBy", "Value": "platform-cli"},
                    {"Key": "Owner", "Value": _username()},
                ]
            }],
        }
        if key_name:
            kwargs["KeyName"] = key_name
        if subnet_id:
            kwargs["SubnetId"] = subnet_id
        if sg_id:
            kwargs["SecurityGroupIds"] = list(sg_id)  # IDs only

        resp = ec2.run_instances(**kwargs)
        iid = resp["Instances"][0]["InstanceId"]
        click.echo(f"instance created: {iid}")
    except ClientError as e:
        click.echo(f"error creating instance: {e}", err=True)

@ec2_group.command("list")
def list_instances():
    """List platform-cli instances"""
    paginator = ec2.get_paginator("describe_instances")
    filters = [{"Name": "tag:CreatedBy", "Values": ["platform-cli"]}]
    any_found = False
    for page in paginator.paginate(Filters=filters):
        for r in page.get("Reservations", []):
            for i in r.get("Instances", []):
                any_found = True
                tags = {t["Key"]: t["Value"] for t in i.get("Tags", [])}
                click.echo(
                    f"{tags.get('Name','-')}\t{i['InstanceId']}\t{i['State']['Name']}\t{i['InstanceType']}\t{ i.get('PublicIpAddress','-') }"
                )
    if not any_found:
        click.echo("No platform-cli instances found.")

@ec2_group.command("start")
@click.option("--id", "iid", required=True, help="InstanceId")
def start_instance(iid):
    _ensure_cli_instance(iid)
    try:
        ec2.start_instances(InstanceIds=[iid])
        click.echo("starting...")
    except ClientError as e:
        click.echo(f"error starting: {e}", err=True)

@ec2_group.command("stop")
@click.option("--id", "iid", required=True, help="InstanceId")
def stop_instance(iid):
    _ensure_cli_instance(iid)
    try:
        ec2.stop_instances(InstanceIds=[iid])
        click.echo("stopping...")
    except ClientError as e:
        click.echo(f"error stopping: {e}", err=True)

@ec2_group.command("terminate")
@click.option("--id", "iid", required=True, help="InstanceId")
def terminate_instance(iid):
    _ensure_cli_instance(iid)
    try:
        ec2.terminate_instances(InstanceIds=[iid])
        click.echo("terminating...")
    except ClientError as e:
        click.echo(f"error terminating: {e}", err=True)

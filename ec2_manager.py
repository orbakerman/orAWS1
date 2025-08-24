import boto3
import os
from botocore.exceptions import ClientError
from utils import get_latest_ami, get_cli_instances, tag_resource

ec2 = boto3.resource('ec2')
client = boto3.client('ec2')

def handle_ec2(action, params):
    if action == 'create':
        create_instance(params)
    elif action == 'list':
        list_instances()
    elif action == 'start':
        start_instance(params)
    elif action == 'stop':
        stop_instance(params)
    else:
        print(f"not spourted action: {action}")

def create_instance(params):
    username = os.getenv("USER") or os.getenv("USERNAME")
    instance_type = params.get('type', 't3.micro')

    if instance_type not in ['t3.micro', 't2.small']:
        print("error: you can only create t3.micro or t2.small.")
        return

    # checking instances count
    running = get_cli_instances(state='running')
    if len(running) >= 2:
        print("error: max of 2 instances CLI.")
        return

    ami_id = get_latest_ami(params.get('ami', 'ubuntu'))

    print(f"user of AMI: {ami_id}")

    try:
        instances = ec2.create_instances(
            ImageId=ami_id,
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'CreatedBy', 'Value': 'platform-cli'},
                    {'Key': 'Owner', 'Value': username or 'unknown'}
                ]
            }]
        )
        instance = instances[0]
        print(f"instance created: {instance.id}")
    except ClientError as e:
        print(f"error AWS: {e}")

def list_instances():
    instances = get_cli_instances()
    for inst in instances:
        print(f"{inst.id} - {inst.state['Name']} - {inst.instance_type}")

def start_instance(params):
    instance_id = params.get('id')
    inst = ec2.Instance(instance_id)
    if is_cli_instance(inst):
        inst.start()
        print(f"instance {instance_id} started.")
    else:
        print("error: only instances sporrted 'CreatedBy=platform-cli' .")

def stop_instance(params):
    instance_id = params.get('id')
    i

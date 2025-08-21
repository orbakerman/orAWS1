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
        print(f"פעולה לא נתמכת: {action}")

def create_instance(params):
    username = os.getenv("USER") or os.getenv("USERNAME")
    instance_type = params.get('type', 't3.micro')

    if instance_type not in ['t3.micro', 't2.small']:
        print("שגיאה: ניתן ליצור רק t3.micro או t2.small.")
        return

    # בדיקה האם יש כבר 2 אינסטנסים פעילים מה-CLI
    running = get_cli_instances(state='running')
    if len(running) >= 2:
        print("שגיאה: ניתן להפעיל רק עד 2 אינסטנסים דרך ה-CLI.")
        return

    ami_id = get_latest_ami(params.get('ami', 'ubuntu'))

    print(f"משתמש ב-AMI: {ami_id}")

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
        print(f"אינסטנס נוצר: {instance.id}")
    except ClientError as e:
        print(f"שגיאת AWS: {e}")

def list_instances():
    instances = get_cli_instances()
    for inst in instances:
        print(f"{inst.id} - {inst.state['Name']} - {inst.instance_type}")

def start_instance(params):
    instance_id = params.get('id')
    inst = ec2.Instance(instance_id)
    if is_cli_instance(inst):
        inst.start()
        print(f"האינסטנס {instance_id} הופעל.")
    else:
        print("שגיאה: רק אינסטנסים עם תג 'CreatedBy=platform-cli' נתמכים.")

def stop_instance(params):
    instance_id = params.get('id')
    i

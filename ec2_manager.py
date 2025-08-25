import boto3
import click

ec2 = boto3.client('ec2')

@click.group()
def ec2_group():
    """Manage EC2 instances"""
    pass

@ec2_group.command('start')
@click.option('--ami', required=True, help='AMI ID to launch')
@click.option('--instance-type', default='t2.micro', help='EC2 instance type')
@click.option('--key-name', required=True, help='Key pair name')
@click.option('--security-group', required=True, help='Security group name')
def start_instance(ami, instance_type, key_name, security_group):
    """Start an EC2 instance"""
    try:
        response = ec2.run_instances(
            ImageId=ami,
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            KeyName=key_name,
            SecurityGroups=[security_group]
        )
        instance_id = response['Instances'][0]['InstanceId']
        click.echo(f"EC2 instance started: {instance_id}")
    except Exception as e:
        click.echo(f"Error launching EC2 instance: {e}")

@ec2_group.command('list')
def list_instances():
    """List all EC2 instances"""
    try:
        response = ec2.describe_instances()
        reservations = response['Reservations']
        if not reservations:
            click.echo("No EC2 instances found.")
            return
        for reservation in reservations:
            for instance in reservation['Instances']:
                state = instance['State']['Name']
                instance_id = instance['InstanceId']
                click.echo(f"Instance ID: {instance_id}, State: {state}")
    except Exception as e:
        click.echo(f"Error listing EC2 instances: {e}")

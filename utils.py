import boto3
import getpass


def get_cli_instances(state=None):
    """
    Returns EC2 instances that were created by platform-cli.
    Optionally filter by instance state (e.g., 'running', 'stopped').
    """
    ec2 = boto3.resource('ec2')
    filters = [{'Name': 'tag:CreatedBy', 'Values': ['platform-cli']}]
    if state:
        filters.append({'Name': 'instance-state-name', 'Values': [state]})
    return ec2.instances.filter(Filters=filters)


def get_latest_ami(os_name='ubuntu'):
    """
    Retrieves the latest official AMI ID from AWS SSM Parameter Store,
    based on the specified OS type (ubuntu or amazonlinux).
    """
    ssm = boto3.client('ssm')

    if os_name == 'ubuntu':
        param_name = '/aws/service/canonical/ubuntu/server/latest/stable/amd64/hvm/ebs-gp2/ami-id'
    elif os_name == 'amazonlinux':
        param_name = '/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2'
    else:
        raise ValueError("Unsupported OS name")

    try:
        response = ssm.get_parameter(Name=param_name)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Error retrieving AMI: {e}")
        return None


def tag_resource(resource_id, resource_type='ec2', owner=None):
    """
    Adds tags to an AWS resource:
    - CreatedBy=platform-cli
    - Owner=<your-username>

    Supported resource types: 'ec2', 's3', 'route53'
    """
    if not owner:
        owner = getpass.getuser()

    tags = [
        {'Key': 'CreatedBy', 'Value': 'platform-cli'},
        {'Key': 'Owner', 'Value': owner}
    ]

    if resource_type == 'ec2':
        ec2 = boto3.client('ec2')
        ec2.create_tags(Resources=[resource_id], Tags=tags)

    elif resource_type == 's3':
        s3 = boto3.client('s3')
        tag_set = {'TagSet': [{'Key': t['Key'], 'Value': t['Value']} for t in tags]}
        s3.put_bucket_tagging(Bucket=resource_id, Tagging=tag_set)

    elif resource_type == 'route53':
        tagging = boto3.client('resourcegroupstaggingapi')
        arn = f'arn:aws:route53:::hostedzone/{resource_id}'
        tagging.tag_resources(
            ResourceARNList=[arn],
            Tags={t['Key']: t['Value'] for t in tags}
        )

    else:
        raise ValueError(f"Unsupported resource type: {resource_type}")

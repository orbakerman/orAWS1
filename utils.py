import boto3

def get_cli_instances(state=None):
    ec2 = boto3.resource('ec2')
    filters = [{'Name': 'tag:CreatedBy', 'Values': ['platform-cli']}]
    if state:
        filters.append({'Name': 'instance-state-name', 'Values': [state]})
    return ec2.instances.filter(Filters=filters)

def get_latest_ami(os_name='ubuntu'):
    ssm = boto3.client('ssm')

    if os_name == 'ubuntu':
        param_name = '/aws/service/canonical/ubuntu/server/latest/stable/amd64/hvm/ebs-gp2/ami-id'
    elif os_name == 'amazonlinux':
        param_name = '/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2'
    else:
        raise ValueError("action not sported")

    try:
        response = ssm.get_parameter(Name=param_name)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"error finding AMI: {e}")
        return None

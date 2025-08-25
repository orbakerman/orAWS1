import click
from ec2_manager import ec2_group
from s3_manager import s3_group
from route53_manager import route53_group

@click.group()
def cli():
    """platform-cli: AWS resource manager (EC2, S3, Route53)"""
    pass

cli.add_command(ec2_group, name='ec2')
cli.add_command(s3_group, name='s3')
cli.add_command(route53_group, name='route53')

if __name__ == '__main__':
    cli()


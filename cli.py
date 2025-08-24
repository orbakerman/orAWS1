import click
from ec2_manager import handle_ec2
from s3_manager import handle_s3
from route53_manager import handle_route53


@click.group()
def cli():
    """platform-cli: resurs managemant AWS (EC2, S3, Route53)"""
    pass


@cli.command()
@click.argument('resource', type=click.Choice(['ec2', 's3', 'route53']))
@click.argument('action', type=str)
@click.option('--params', '-p', multiple=True, help='פרמטרים לפעולה (key=value)')
def run(resource, action, params):
    """resuress: EC2, S3, Route53"""
    param_dict = dict(p.split('=') for p in params)

    if resource == 'ec2':
        handle_ec2(action, param_dict)
    elif resource == 's3':
        handle_s3(action, param_dict)
    elif resource == 'route53':
        handle_route53(action, param_dict)


if __name__ == '__main__':
    cli()

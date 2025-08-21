import click
from ec2_manager import ec2_cli

@click.group()
def cli():
    """Platform CLI to manage AWS resources."""
    pass

cli.add_command(ec2_cli, name='ec2')


if __name__ == "__main__":
    cli()

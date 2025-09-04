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
from cleanup import cleanup_resources  # ייבוא הפונקציה מקובץ cleanup.py

@cli.command("cleanup")
@click.option("--yes", is_flag=True, help="דלג על שאלה ומחק מיד")
@click.option("--dry-run", is_flag=True, help="הצגה בלבד (לא מוחק בפועל)")
def cleanup_cmd(yes, dry_run):
    """מוחק את כל המשאבים עם CreatedBy=platform-cli (EC2/S3/Route53)"""
    if not yes and not dry_run:
        confirm = input("פעולה הרסנית! למחוק את כל משאבי platform-cli? הקלידי YES: ")
        if confirm.strip().lower() != "yes":
            click.echo("בוטל.")
            return
    cleanup_resources(dry_run=dry_run)

if __name__ == '__main__':
    cli()


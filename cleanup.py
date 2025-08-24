import boto3

def cleanup_resources():
    print(" cleanup of the platform-cli...")

    cleanup_ec2()
    cleanup_s3()
    cleanup_route53()

    print("clean up scessed")

def cleanup_ec2():
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.filter(Filters=[
        {'Name': 'tag:CreatedBy', 'Values': ['platform-cli']}
    ])

    to_terminate = [inst.id for inst in instances]
    if to_terminate:
        print(f"deleting : {to_terminate}")
        ec2.instances.filter(InstanceIds=to_terminate).terminate()
    else:
        print("no more instances.")

def cleanup_s3():
    s3 = boto3.client('s3')
    s3_resource = boto3.resource('s3')
    buckets = s3.list_buckets()

    for b in buckets['Buckets']:
        bucket_name = b['Name']
        try:
            tagging = s3.get_bucket_tagging(Bucket=bucket_name)
            tags = {tag['Key']: tag['Value'] for tag in tagging['TagSet']}
            if tags.get('CreatedBy') == 'platform-cli':
                print(f"cleaning buckets : {bucket_name}")
                # delete buckets
                bucket = s3_resource.Bucket(bucket_name)
                bucket.objects.all().delete()
                # final deleting
                try:
                    bucket.object_versions.all().delete()
                except:
                    pass
                bucket.delete()
        except:
            continue

def cleanup_route53():
    route53 = boto3.client('route53')
    zones = route53.list_hosted_zones()['HostedZones']

    for zone in zones:
        zone_id = zone['Id'].split('/')[-1]
        try:
            tags_response = route53.list_tags_for_resource(
                ResourceType='hostedzone',
                ResourceId=zone_id
            )
            tags = {tag['Key']: tag['Value'] for tag in tags_response['ResourceTagSet']['Tags']}
            if tags.get('CreatedBy') == 'platform-cli':
                # dns deleting
                records = route53.list_resource_record_sets(HostedZoneId=zone_id)
                changes = []
                for record in records['ResourceRecordSets']:
                    if record['Type'] not in ['NS', 'SOA']:
                        changes.append({
                            'Action': 'DELETE',
                            'ResourceRecordSet': record
                        })
                if changes:
                    route53.change_resource_record_sets(
                        HostedZoneId=zone_id,
                        ChangeBatch={'Changes': changes}
                    )
                # מחיקת הזון
                print(f"deleting Hosted Zone: {zone['Name']} ({zone_id})")
                route53.delete_hosted_zone(Id=zone_id)
        except:
            continue

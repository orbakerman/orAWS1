import boto3
import os

route53 = boto3.client('route53')

def handle_route53(action, params):
    if action == 'create':
        create_zone(params)
    elif action == 'list':
        list_zones()
    elif action == 'update':
        upsert_record(params)
    elif action == 'delete':
        delete_record(params)
    else:
        print(f"שגיאה: פעולה לא נתמכת - {action}")

def create_zone(params):
    domain = params.get('domain')
    username = os.getenv("USER") or os.getenv("USERNAME") or "unknown"

    if not domain:
        print("שגיאה: חובה לציין --params domain=example.com")
        return

    try:
        response = route53.create_hosted_zone(
            Name=domain,
            CallerReference=str(hash(domain)),
            HostedZoneConfig={
                'Comment': 'Created by platform-cli',
                'PrivateZone': False
            },
            Tags=[
                {'Key': 'CreatedBy', 'Value': 'platform-cli'},
                {'Key': 'Owner', 'Value': username}
            ]
        )
        print(f"✅ אזור DNS נוצר: {domain}")
    except Exception as e:
        print(f"שגיאה ביצירת Hosted Zone: {e}")

def list_zones():
    try:
        zones = route53.list_hosted_zones()['HostedZones']
        for zone in zones:
            zone_id = zone['Id'].split('/')[-1]
            tags = get_zone_tags(zone_id)
            if tags.get('CreatedBy') == 'platform-cli':
                print(f"🌐 {zone['Name']} (ID: {zone_id})")
    except Exception as e:
        print(f"שגיאה בשליפת אזורים: {e}")

def get_zone_tags(zone_id):
    try:
        response = route53.list_tags_for_resource(
            ResourceType='hostedzone',
            ResourceId=zone_id
        )
        return {tag['Key']: tag['Value'] for tag in response['ResourceTagSet']['Tags']}
    except:
        return {}

def upsert_record(params):
    zone_id = params.get('zone_id')
    record_name = params.get('name')
    record_type = params.get('type', 'A')
    record_value = params.get('value')

    if not zone_id or not record_name or not record_value:
        print("שגיאה: חובה לציין --params zone_id=... name=... value=...")
        return

    if not is_cli_zone(zone_id):
        print("שגיאה: ניתן לערוך רק אזורים שנוצרו על ידי CLI.")
        return

    try:
        route53.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                'Comment': 'Managed by platform-cli',
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': record_name,
                            'Type': record_type,
                            'TTL': 300,
                            'ResourceRecords': [{'Value': record_value}]
                        }
                    }
                ]
            }
        )
        print(f"✅ רשומה עודכנה/נוצרה: {record_name} → {record_value}")
    except Exception as e:
        print(f"שגיאה ביצירת רשומה: {e}")

def delete_record(params):
    zone_id = params.get('zone_id')
    record_name = params.get('name')
    record_type = params.get('type', 'A')
    record_value = params.get('value')

    if not zone_id or not record_name or not record_value:
        print("שגיאה: חובה לציין --params zone_id=... name=... value=...")
        return

    if not is_cli_zone(zone_id):
        print("שגיאה: ניתן למחוק רק רשומות מאזור שנוצר על ידי CLI.")
        return

    try:
        route53.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                'Comment': 'Managed by platform-cli',
                'Changes': [
                    {
                        'Action': 'DELETE',
                        'ResourceRecordSet': {
                            'Name': record_name,
                            'Type': record_type,
                            'TTL': 300,
                            'ResourceRecords': [{'Value': record_value}]
                        }
                    }
                ]
            }
        )
        print(f"🗑️ רשומה נמחקה: {record_name}")
    except Exception as e:
        print(f"שגיאה במחיקת רשומה: {e}")

def is_cli_zone(zone_id):
    tags = get_zone_tags(zone_id)
    return tags.get('CreatedBy') == 'platform-cli'

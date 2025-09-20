import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')

    # --- Delete unused snapshots ---
    paginator = ec2.get_paginator('describe_snapshots')
    for page in paginator.paginate(OwnerIds=['self']):
        for snapshot in page.get('Snapshots', []):
            snapshot_id = snapshot['SnapshotId']
            volume_id = snapshot.get('VolumeId')

            if not volume_id:
                try:
                    ec2.delete_snapshot(SnapshotId=snapshot_id)
                    print(f"Deleted snapshot {snapshot_id} (no volume attached).")
                except ClientError as e:
                    print(f"Error deleting snapshot {snapshot_id}: {e}")
            else:
                try:
                    volume_response = ec2.describe_volumes(VolumeIds=[volume_id])
                    volume = volume_response['Volumes'][0]
                    if not volume.get('Attachments'):  # volume exists but unattached
                        ec2.delete_snapshot(SnapshotId=snapshot_id)
                        print(f"Deleted snapshot {snapshot_id} (volume unattached).")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'InvalidVolume.NotFound':
                        try:
                            ec2.delete_snapshot(SnapshotId=snapshot_id)
                            print(f"Deleted snapshot {snapshot_id} (volume missing).")
                        except ClientError as e2:
                            print(f"Error deleting snapshot {snapshot_id}: {e2}")
                    else:
                        print(f"Unexpected error for snapshot {snapshot_id}: {e}")

    # --- Delete unattached EBS volumes ---
    try:
        volumes = ec2.describe_volumes(Filters=[{'Name': 'status', 'Values': ['available']}])
        for volume in volumes.get('Volumes', []):
            volume_id = volume['VolumeId']
            try:
                ec2.delete_volume(VolumeId=volume_id)
                print(f"Deleted unattached volume {volume_id}.")
            except ClientError as e:
                print(f"Error deleting volume {volume_id}: {e}")
    except ClientError as e:
        print(f"Error listing volumes: {e}")

    return {"status": "Cleanup completed"}

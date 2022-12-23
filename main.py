import boto3

# Set up the AWS clients
ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')


# Create a key pair if it doesn't exist
# try:
#     key_pair = ec2.create_key_pair(KeyName='key1')
#     key_pair_name = key_pair['KeyName']
# except ec2.exceptions.InvalidKeyPair.Duplicate:
#     # Key pair already exists, get its name
#     key_pair_name = 'key1'

try:
    key_pair = ec2.create_key_pair(KeyName='key1')
    key_pair_name = key_pair['KeyName']
except ec2.exceptions.InvalidKeyPair as e:
    if e.response['Error']['Code'] == 'InvalidKeyPair.Duplicate':
        # Key pair already exists, get its name
        key_pair_name = 'key1'
    else:
        # Some other error occurred, re-raise the exception
        raise

# except Exception as e:
#     # code to handle the exception
#     print(type(e))  # print the type of the exception
exit()
# Create a security group if it doesn't exist
try:
    security_group = ec2.create_security_group(
        GroupName='my-security-group',
        Description='Security group for MySQL server'
    )
    security_group_id = security_group['GroupId']
except ec2.exceptions.InvalidGroup.DuplicateGroup:
    # Security group already exists, get its ID
    response = ec2.describe_security_groups(GroupNames=['my-security-group'])
    security_group_id = response['SecurityGroups'][0]['GroupId']

# Add an inbound rule to the security group to allow all traffic from any IP address
ec2.authorize_security_group_ingress(
    GroupId=security_group_id,
    IpPermissions=[
        {
            'IpProtocol': '-1',
            'FromPort': -1,
            'ToPort': -1,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }
    ]
)

# Define the parameters for the EC2 instance
instance_params = {
    'ImageId': 'ami-0ac019f4fcb7cb7e6',  # Amazon Linux 2 AMI
    'InstanceType': 't2.micro',
    'MinCount': 1,
    'MaxCount': 1,
    'KeyName': key_pair_name,
    'SecurityGroupIds': [security_group_id],
    'UserData': """#!/bin/bash
        yum update -y
        yum install -y mysql
        systemctl start mysqld
        """,
}

# Create the EC2 instance
response = ec2.run_instances(**instance_params)
instance_id = response['Instances'][0]['InstanceId']

# Wait for the instance to be in the 'running' state
ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])

import boto3


class Deployer:

    # Set up the AWS clients
    ec2 = boto3.client('ec2')
    ssm = boto3.client('ssm')

    key_pair_name = ''
    security_group_id = ''
    sa_instance_id = ''
    sa_public_ip = ''

    def __init__(self):
        try:
            key_pair = self.ec2.create_key_pair(KeyName='project_key')
            self.key_pair_name = key_pair['KeyName']
        except Exception as e:
            if e.response['Error']['Code'] == 'InvalidKeyPair.Duplicate':
                # Key pair already exists, get its name
                self.key_pair_name = 'project_key'
            else:
                # Some other error occurred, re-raise the exception
                raise

        # Create a security group if it doesn't exist
        try:
            security_group = self.ec2.create_security_group(
                GroupName='my-security-group',
                Description='Security group for MySQL server'
            )
            self.security_group_id = security_group['GroupId']
        except Exception as e:
            if e.response['Error']['Code'] == 'InvalidGroup.Duplicate':
                # Security group already exists, get its ID
                response = self.ec2.describe_security_groups(GroupNames=['my-security-group'])
                self.security_group_id = response['SecurityGroups'][0]['GroupId']
            else:
                # Some other error occurred, re-raise the exception
                raise

        # Check if the inbound rule already exists
        response = self.ec2.describe_security_groups(GroupIds=[self.security_group_id])
        inbound_rules = response['SecurityGroups'][0]['IpPermissions']
        rule_exists = False
        for rule in inbound_rules:
            if rule['IpProtocol'] == '-1':
                for range in rule['IpRanges']:
                    if range['CidrIp'] == '0.0.0.0/0':
                        rule_exists = True
                        break

        # Add an inbound rule to the security group to allow all traffic
        #  from any IP address if the rule doesn't already exist
        if not rule_exists:
            self.ec2.authorize_security_group_ingress(
                GroupId=self.security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': '-1',
                        'FromPort': -1,
                        'ToPort': -1,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )

    def create_stand_alone_instance(self):
        # Define the parameters for the EC2 instance
        instance_params = {
            'ImageId': 'ami-0b5eea76982371e91',  # Amazon Linux 2 AMI
            'InstanceType': 't2.micro',
            'MinCount': 1,
            'MaxCount': 1,
            'KeyName': self.key_pair_name,
            'SecurityGroupIds': [self.security_group_id],
            'UserData': """#!/bin/bash
                yum update -y
                yum install -y mysql
                systemctl start mysqld
                """,
        }

        # Create the EC2 instance
        response = self.ec2.run_instances(**instance_params)
        self.sa_instance_id = response['Instances'][0]['InstanceId']

        # Wait for the instance to be in the 'running' state
        self.ec2.get_waiter('instance_running').wait(InstanceIds=[self.sa_instance_id])

        # Get the public IP address of the instance
        instance_info = self.ec2.describe_instances(InstanceIds=[self.sa_instance_id])
        self.sa_public_ip = instance_info['Reservations'][0]['Instances'][0]['PublicIpAddress']



# # Connect to the instance using SSM
# ssm_response = ssm.send_command(
#     InstanceIds=[instance_id],
#     DocumentName='AWS-RunShellScript',
#     Parameters={'commands': ['mysql -u root -e "GRANT ALL PRIVILEGES ON *.* TO root@\'%\' IDENTIFIED BY \'password\'; FLUSH PRIVILEGES;"']},
# )
#
# # Check the status of the command execution
# command_id = ssm_response['Command']['CommandId']
# command_status = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
# while command_status['Status'] not in ['Success', 'Failed']:
#     command_status = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
#
# if command_status['Status'] == 'Success':
#     print('Successfully granted privileges to root user from any IP address')
# else:
#     print('Failed to grant privileges to root user')

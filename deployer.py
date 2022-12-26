import boto3
import re


class Deployer:
    # Set up the AWS clients
    ec2 = boto3.client('ec2')
    ssm = boto3.client('ssm')

    key_pair_name = ''
    security_group_id = ''
    standalone_security_group_id = ''
    subnet_id = ''

    sa_instance_id = ''
    proxy_instance_id = ''
    cluster_instance_ids = {
        'master': '',
        'slaves': [],
    }

    def __init__(self):
        try:
            key_pair = self.ec2.create_key_pair(KeyName='project_key')
            self.key_pair_name = key_pair['KeyName']
        except Exception as e:
            if e.response['Error']['Code'] != 'InvalidKeyPair.Duplicate':
                # Some other error occurred, re-raise the exception
                raise
            # Key pair already exists, get its name
            self.key_pair_name = 'project_key'

        response = self.ec2.describe_vpcs(Filters=[{'Name': 'cidr', 'Values': ['10.0.1.0/24']}])

        # Get the list of VPCs
        vpcs = response['Vpcs']

        # Check if the VPC exists
        if vpcs:
            # VPC already exists, get its ID
            vpc_id = response['Vpcs'][0]['VpcId']
        else:
            # Create a VPC if it doesn't exist
            vpc = self.ec2.create_vpc(CidrBlock='10.0.1.0/24')
            vpc_id = vpc['Vpc']['VpcId']

        # Create standalone group if it doesn't exist
        try:
            security_group = self.ec2.create_security_group(
                GroupName='sa-security-group',
                Description='Security group for standalone MySQL server'
            )
            self.standalone_security_group_id = security_group['GroupId']
        except Exception as e:
            if e.response['Error']['Code'] != 'InvalidGroup.Duplicate':
                # Some other error occurred, re-raise the exception
                raise
            # Security group already exists, get its ID
            response = self.ec2.describe_security_groups(GroupNames=['sa-security-group'])
            self.standalone_security_group_id = response['SecurityGroups'][0]['GroupId']

        # Create sql group if it doesn't exist
        try:
            security_group = self.ec2.create_security_group(
                GroupName='sql-security-group',
                Description='Security group for MySQL server',
                VpcId=vpc_id
            )
            self.security_group_id = security_group['GroupId']
        except Exception as e:
            if e.response['Error']['Code'] != 'InvalidGroup.Duplicate':
                # Some other error occurred, re-raise the exception
                raise
            # Security group already exists, get its ID
            response = self.ec2.describe_security_groups(GroupNames=['sql-security-group'])
            self.security_group_id = response['SecurityGroups'][0]['GroupId']

        # Check if the inbound rule already exists for
        self.create_inbound_rule(self.standalone_security_group_id)
        self.create_inbound_rule(self.security_group_id)

        # Check if subnet exists
        response = self.ec2.describe_subnets(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}, {'Name': 'cidr', 'Values': ['10.0.1.0/24']}])

        # Get the list of subnets
        subnets = response['Subnets']

        if subnets:
            # Subnet already exists, get its ID
            self.subnet_id = subnets[0]['SubnetId']
        else:
            # Create a subnet if it doesn't exist
            subnet = self.ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
            self.subnet_id = subnet['Subnet']['SubnetId']

    def create_inbound_rule(self, security_group_id):
        response = self.ec2.describe_security_groups(GroupIds=[security_group_id])
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

    def create_standalone_instance(self):

        """Create and start a standalone EC2 instance.
        After being run, saves the instance ID.
        """
        # Create the standalone instance
        response = self.ec2.run_instances(**self.generate_params('standalone'))
        self.sa_instance_id = response['Instances'][0]['InstanceId']

        # Wait for the instance to be running
        self.ec2.get_waiter('instance_running').wait(InstanceIds=[self.sa_instance_id])

        # Potential code to obtain benchmark results directly, unfortunately ssm does not seem to work on the ubuntu AMI

        # def get_benchmark_results():
        #     # Wait for userData script to run
        #     self.ec2.get_waiter('instance_status_ok').wait(InstanceIds=[self.sa_instance_id])
        #
        #     # Connect to the instance using SSM
        #     res = self.ssm.send_command(
        #         InstanceIds=[self.sa_instance_id],
        #         DocumentName='AWS-RunShellScript',
        #         Parameters={'commands': ['cat /root/benchmark.txt']},
        #     )
        #
        #     # Wait for the command to be completed
        #     command_id = res['Command']['CommandId']
        #     self.ssm.get_waiter('command_success').wait(CommandId=command_id)
        #
        #     # Get the command output
        #     output = self.ssm.get_command_invocation(CommandId=command_id, InstanceId=self.sa_instance_id)
        #     return output['StandardOutputContent']
        #
        # return get_benchmark_results

    def create_cluster(self):
        """Create a cluster of EC2 instances.
        After creating the cluster with specific private ips for the master and the tree slaves, waits for
        them to start. Also saves their ids by the end.
        """
        # Create the Master
        response = self.ec2.run_instances(**self.generate_params('master', '10.0.1.10'))
        self.cluster_instance_ids['master'] = response['Instances'][0]['InstanceId']

        for i in range(1, 4):
            # Create slave i instance
            response = self.ec2.run_instances(**self.generate_params(f'slave_{i}', f'10.0.1.{10+i}'))
            self.cluster_instance_ids['slaves'].append(response['Instances'][0]['InstanceId'])

        # Wait for all the instances to be running
        self.ec2.get_waiter('instance_running').wait(InstanceIds=[self.cluster_instance_ids['master']])
        for id in self.cluster_instance_ids['slaves']:
            self.ec2.get_waiter('instance_running').wait(InstanceIds=[id])

    def generate_params(self, instance_name, private_ip=None):
        """Generate parameters for creating an EC2 instance.

        :param instance_name: name of the instance
        :param private_ip: private IP address for the instance (optional)
        :returns: dictionary of parameters for the `run_instances` method
        """
        # Define the parameters for the EC2 instance
        user_data_script_name = re.sub(r'_\d', '', instance_name) + '_user_data.sh'
        params = {
            'ImageId': 'ami-0574da719dca65348',  # Ubuntu AMI
            'TagSpecifications': [{
                    'ResourceType': 'instance',
                    'Tags': [{
                        'Key': 'Name',
                        'Value': instance_name
                    }]
            }],
            'InstanceType': 't2.micro',
            'MinCount': 1,
            'MaxCount': 1,
            'KeyName': self.key_pair_name,
            'SecurityGroupIds': [self.standalone_security_group_id],
            'UserData': open(user_data_script_name, 'r').read(),
        }

        # If cluster or proxy, set the subnet and security group ID for the instance, and specify the private IP address
        if private_ip is not None:
            params['SubnetId'] = self.subnet_id
            params['PrivateIpAddress']: private_ip
            params['SecurityGroupIds'] = [self.security_group_id]
        return params

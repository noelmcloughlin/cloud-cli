#!/usr/bin/env python3

import sys
import os
import getopt
import boto3
import botocore
#sys.path.append('./lib')

### VARS ###

ec2_keypair_name='ec2_user'
ec2_ami='ami-0fad7378adf284ce0'
ec2_ami_type='t2.micro'
ec2_cidr_block='10.0.0.0/16'
ec2_elastic_ip_allocation_id=None
ec2_elastic_ip_association_id=None
ec2_group_name='mygroupname'
ec2_instance_id=None
ec2_internet_gateway_id=None
ec2_project_name='assignment project'
ec2_region_name='eu-west-1'
ec2_sg_id=None
ec2_subnet_id=None
ec2_tenancy='default'
ec2_vpc_id=None
ec2_userdata="""
#!/bin/bash
yum update -y
amazon-linux-extras install -y lamp-mariadb10.2-php7.2 php7.2
yum install -y httpd mariadb-server
systemctl start httpd
systemctl enable httpd
usermod -a -G apache ec2-user
chown -R ec2-user:apache /var/www
chmod 2775 /var/www
find /var/www -type d -exec chmod 2775 {} \;
find /var/www -type f -exec chmod 0664 {} \;
echo "<?php phpinfo(); ?>" > /var/www/html/phpinfo.php
"""


### FUNCTIONS ####

def usage():
    print("\n%s Usage:" % os.path.basename(__file__))
    print("\n\t  -a --action\tstart|clean|info\tInteract with EC2 environment.")
    print("\n\t[ -t --target\tec2 ]\t\t\tEC2 target")
    print("\n\t[ -k --keypair\t<name> ]\t\tAWS keypair name")
    print("\n")
    sys.exit(2)

def handle(error):
    try:
        if error.response['Error']['Code'] in ('DryRunOperation',):
            return
        elif error.response['Error']['Code'] in ('DependencyViolation', 'InvalidGroup.NotFound', 'VpcLimitExceeded', 'UnauthorizedOperation', 'ParamValidationError', 'AddressLimitExceeded',):
            print('Failed (%s)' % error.response['Error']['Code'])
        else:
            print("Failed with %s" % error)
    except AttributeError as err:
        print('Something went wrong %s' % err)
    exit(1)

#################
### KEYPAIRS ###
#################

def get_keypairs(client, name='key-name', value=ec2_keypair_name, mode=True):
    """
    Get keypairs
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_key_pairs
    """
    try:
        return client.describe_key_pairs(Filters=[{'Name': name, 'Values': [value,]},], DryRun=mode)
    except Exception as err:
        handle(err)


############
### VPCS ###
############

def create_vpc(client, name=ec2_project_name, cidr_ipv4=ec2_cidr_block, autoipv6=False, tenancy=ec2_tenancy, mode=True):
    """
    Create a virtual private cloud.
    See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.create_vpc
    """
    try:
        vpc = client.create_vpc(CidrBlock=ec2_cidr_block, AmazonProvidedIpv6CidrBlock=True, InstanceTenancy=tenancy, DryRun=mode)
        return vpc
    except Exception as err:
        handle(err)
    return None

def delete_vpc(client, vpc_id=ec2_vpc_id, mode=True):
    """
    Delete a virtual private cloud.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.delete_vpc
    """
    try:
        print('Deleting %s %s' % (vpc_id, '(dryrun)' if mode else ''))
        return client.delete_vpc(VpcId=vpc_id, DryRun=mode)
    except Exception as err:
        handle(err)

def get_vpcs(client, name='tag:project', value=ec2_project_name, mode=True):
    """
    Get VPC(s) by tag.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_vpcs
    """
    try:
        return client.describe_vpcs(Filters=[{'Name': name, 'Values': [value,]},], DryRun=mode)
    except Exception as err:
        handle(err)

##############
### SUBNET ###
##############

def create_subnet(client, name=ec2_project_name, cidr_ipv4=ec2_cidr_block, vpc_id=ec2_vpc_id, mode=True):
    """
    Create a subnet.
    See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.create_subnet
    """
    try:
        return client.create_subnet(CidrBlock=ec2_cidr_block, VpcId=vpc_id, DryRun=mode)
    except Exception as err:
        handle(err)
    return None

def delete_subnet(client, subnet=ec2_subnet_id, mode=True):
    """
    Delete a subnet.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.delete_subnet
    """
    try:
        print('Deleting %s %s' % (subnet, '(dryrun)' if mode else ''))
        return client.delete_subnet(SubnetId=subnet, DryRun=mode)
    except Exception as err:
        handle(err)

def get_subnets(client, name='tag:project', value=ec2_project_name, mode=True):
    """
    Get VPC(s) by tag (note: create_tags not working via client api, use cidr or object_id instead )
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_subnets
    """
    try:
        return client.describe_subnets(Filters=[{'Name': name, 'Values': [value,]},], DryRun=mode)
    except Exception as err:
        handle(err)

#######################
### SECURITY GROUPS ###
#######################

def create_sg(client, desc=ec2_project_name, groupname=ec2_group_name, vpc=ec2_vpc_id, mode=True):
    """
    Create security group.
    See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.create_security_group
    """
    try:
        return client.create_security_group( Description=desc, GroupName=groupname, VpcId=vpc, DryRun=mode)
    except Exception as err:
        handle(err)

def delete_sg(client, groupid=ec2_sg_id, mode=True):
    """
    Delete a security group.
    See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.delete_security_group
    """
    try:
        print('Deleting %s %s' % (groupid, '(dryrun)' if mode else ''))
        return client.delete_security_group( GroupId=groupid, DryRun=mode)
    except Exception as err:
        handle(err)

def get_sgs(client, name='tag:project', value=ec2_project_name, groupname=ec2_group_name, mode=True):
    """
    Get Security Groups by searching for VPC Id.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_security_groups
    """
    try:
        return client.describe_security_groups(Filters=[{'Name': name, 'Values': [value,]}, {'Name': 'group-name', 'Values': [groupname,]},], DryRun=mode)
    except Exception as err:
        handle(err)

def add_sg_ingress(client, fromport=80, toport=80, ipprotocol='TCP', ipranges=[{'CidrIp': '0.0.0.0/0'},], ipv6ranges=[{'CidrIpv6', '::/0'},], groupid=ec2_sg_id, mode=True):
    """
    Adds one or more ingress rules to a security group.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.authorize_security_group_ingress
    """
    try:
        return client.authorize_security_group_ingress(IpPermissions=[{'FromPort': fromport, 'ToPort': toport, 'IpProtocol': ipprotocol, 'IpRanges': ipranges, 'Ipv6Ranges': ipv6ranges},], GroupId=groupid, DryRun=mode)
    except Exception as err:
        handle(err)

###################
### ELASTIC IPS ###
###################

def create_elastic_ip(client, domain='vpc', mode=True):
    """
    Create elastic ip.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.allocate_address
    """
    try:
        return client.allocate_address( Domain=domain, DryRun=mode)
    except Exception as err:
        handle(err)

def associate_elastic_ip(client, allocation_id=ec2_elastic_ip_allocation_id, instance_id=ec2_instance_id, mode=True):
    """
    Associate elastic ip.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.associate_address
    """
    try:
        return client.associate_address( AllocationId=allocation_id, InstanceId=instance_id, DryRun=mode)
    except Exception as err:
        handle(err)

def delete_elastic_ip(client, allocation_id=ec2_elastic_ip_allocation_id, public_ip='', mode=True):
    """
    Delete a elastic ip.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.release_address
    """
    try:
        print('Deleting %s %s %s' % (allocation_id, public_ip, '(dryrun)' if mode else ''))
        client.release_address( AllocationId=allocation_id, DryRun=mode)
    except Exception as err:
        handle(err)

def get_elastic_ips(client, name='domain', value='vpc', allocation_id=ec2_elastic_ip_allocation_id, instance_id=ec2_instance_id, mode=True):
    """
    Get Elastic IPs by searching for stuff
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_addresses
    """
    try:
        if allocation_id:
            return client.describe_addresses(Filters=[{'Name': name, 'Values': [value,]},], AllocationIds=[allocation_id,], DryRun=mode)
        elif instance_id:
            return client.describe_addresses(Filters=[{'Name': name, 'Values': [value,]}, {'Name': 'instance-id', 'Values': [instance_id,]},], DryRun=mode)
        else:
            return client.describe_addresses(Filters=[{'Name': name, 'Values': [value,]},], DryRun=mode)
    except Exception as err:
        handle(err)


########################
### INTERNET GATEWAY ###
########################

def create_internet_gateway(client, mode=True):
    """
    Create internet gateway.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.create_internet_gateway
    """
    try:
        return client.create_internet_gateway(DryRun=mode)
    except Exception as err:
        handle(err)

def delete_internet_gateway(client, gateway_id=ec2_internet_gateway_id, mode=True):
    """
    Delete a internet gateway.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.delete_internet_gateway
    """
    try:
        print('Deleting %s %s' % (gateway_id, '(dryrun)' if mode else ''))
        return client.delete_internet_gateway( InternetGatewayId=gateway_id, DryRun=mode)
    except Exception as err:
        handle(err)

def get_internet_gateways(client, name='attachment.vpc-id', value=ec2_vpc_id, mode=True):
    """
    Get internet gateways IPs by searching for stuff
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_internet_gateways
    """
    try:
        return client.describe_internet_gateways(Filters=[{'Name': name, 'Values': [value,]},], DryRun=mode)
    except Exception as err:
        handle(err)

def attach_internet_gateway(client, gateway_id=ec2_internet_gateway_id, vpc_id=ec2_vpc_id, mode=True):
    """
    Attaches an internet gateway to a VPC
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.attach_internet_gateway
    """
    try:
        print('Attaching %s to %s %s' % ( gateway_id, vpc_id, '(dryrun)' if mode else '' ))
        client.attach_internet_gateway( InternetGatewayId=gateway_id, VpcId=vpc_id, DryRun=mode)
    except Exception as err:
        handle(err)

def detach_internet_gateway(client, gateway_id=ec2_internet_gateway_id, vpc_id=ec2_vpc_id, mode=True):
    """
    Attaches an internet gateway to a VPC
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.detach_internet_gateway
    """
    try:
        print('Detaching %s from %s %s' % ( gateway_id, vpc_id, '(dryrun)' if mode else '' ))
        client.detach_internet_gateway( InternetGatewayId=gateway_id, VpcId=vpc_id, DryRun=mode)
    except Exception as err:
        handle(err)


####################
### EC2 RESOURCE ###
####################

def create_instance(ec2, image_id=ec2_ami, image_type=ec2_ami_type, sg_id=ec2_sg_id, sn_id=ec2_subnet_id, userdata='', key=ec2_keypair_name, mode=True):
    """
    Create and launch a new Amazon EC2 micro instance with boto3.
    Launch a free tier Amazon Linux AMI using your Amazon credentials.
    """
    try:
        print('Creating instance %s' % '(dryrun)' if mode else '' )
        return ec2.create_instances(ImageId=image_id, MaxCount=1, MinCount=1, InstanceType=image_type, SecurityGroupIds=[sg_id,], SubnetId=sn_id, UserData=userdata, KeyName=key, DryRun=mode)
    except Exception as err:
        handle(err)

def delete_instance(instance, instance_id=ec2_instance_id, mode=True):
    """
    Delete a ec2 instance
    See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.delete_security_group
    """
    try:
        print('Terminating instance %s' % '(dryrun)' if mode else '' )
        instance.terminate(DryRun=mode)
        instance.wait_until_terminated(Filters=[{'Name': 'instance-id', 'Values': [instance_id,]},], DryRun=mode)
    except Exception as err:
        handle(err)

def get_instances(client, name='tag:project', value=ec2_project_name, running=False, mode=True):
    """
    Get EC2 instances by searching for stuff
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances
    """
    try:
        if running:
            return client.describe_instances(Filters=[{'Name': name, 'Values': [value,]}, {'Name': 'instance-state-name', 'Values': [running,]},], DryRun=mode)
        else:
            return client.describe_instances(Filters=[{'Name': name, 'Values': [value,]},], DryRun=mode)
    except Exception as err:
        handle(err)


################################
#### cleanup all resources #####
################################
def clean(ec2, client):
    for mode in (True, False):
        try:
            #### VPC ####
            print("\nCLEAN DOWN E2C ENVIRON %s" % ('dryrun' if mode else 'for real, please be patient'))
            vpcs = get_vpcs(client, 'cidr', ec2_cidr_block, mode)
            if vpcs and "Vpcs" in vpcs and vpcs['Vpcs']:
                for vpc in vpcs['Vpcs']:
                    ec2_vpc_id = vpc['VpcId'] 

                    ### EC2 INSTANCES ###
                    instances = get_instances(client, 'vpc-id', ec2_vpc_id, False, mode)
                    if instances and "Reservations" in instances and instances['Reservations']:
                        for v in instances['Reservations'][0]['Instances']:
                            delete_instance(ec2.Instance(v['InstanceId']), v['InstanceId'], mode)
    
                            ### ELASTIC IPS ###
                            eips = get_elastic_ips(client, 'domain', 'vpc', None, v['InstanceId'], mode)
                            if eips:
                                for ip in eips['Addresses']:
                                    delete_elastic_ip(client, ip['AllocationId'], ip['PublicIp'], mode)

                    ### SUBNETS ###
                    subnets = get_subnets(client, 'vpc-id', ec2_vpc_id, mode)
                    if subnets and "Subnets" in subnets and subnets['Subnets']:
                        for sn in subnets['Subnets']:
                            delete_subnet(client, sn['SubnetId'], mode)

                    ### INTERNET GATEWAY ###
                    gateways = get_internet_gateways(client, 'attachment.vpc-id', ec2_vpc_id, mode)
                    if gateways and "InternetGateways" in gateways and gateways['InternetGateways']:
                        for v in gateways['InternetGateways']:
                            detach_internet_gateway(client, v['InternetGatewayId'], ec2_vpc_id, mode) 
                            delete_internet_gateway(client, v['InternetGatewayId'], mode)

                    ### SECURITY GROUPS ###
                    sgs = get_sgs(client, 'vpc-id', ec2_vpc_id, ec2_group_name, mode)
                    if sgs and "SecurityGroups" in sgs and sgs["SecurityGroups"]:
                        for sg in sgs['SecurityGroups']:
                            delete_sg(client, sg['GroupId'], mode)

                    ### VPC ###
                    delete_vpc(client, ec2_vpc_id, mode)
            else:
                print('No VPCs found')
        except Exception as err:
            handle(err)
    return(0)

##########################
#### Create resources ####
##########################
def start(ec2, client):
    for mode in (True, False):
        try:
            print("\nCREATE E2C ENVIRON %s" % ('dryrun' if mode else 'for real, please be patient'))
            ec2_vpc_id = create_vpc(client, ec2_project_name, ec2_cidr_block, True, ec2_tenancy, mode)
            if ec2_vpc_id:
                ec2_vpc_id = ec2_vpc_id['Vpc']['VpcId']

                ### INTERNET GATEWAY
                ec2_gateway_id = create_internet_gateway(client, mode)
                if ec2_gateway_id:
                    ec2_gateway_id = ec2_gateway_id['InternetGateway']['InternetGatewayId']
                    attach_internet_gateway(client, ec2_gateway_id, ec2_vpc_id, mode) 

                ### SUBNET ###
                ec2_subnet_id = create_subnet(client, ec2_project_name, ec2_cidr_block, ec2_vpc_id, mode)
                if ec2_subnet_id:
                    ec2_subnet_id = ec2_subnet_id['Subnet']['SubnetId']

                ### SECURITY GROUP ###
                ec2_sg_id = create_sg(client, ec2_project_name, ec2_group_name, ec2_vpc_id, mode)
                if ec2_sg_id:
                    ec2_sg_id = ec2_sg_id['GroupId']
                    add_sg_ingress(client, 22, 22, 'TCP', [{'CidrIp': '0.0.0.0/0'},], [{'CidrIpv6': '::/0'},], ec2_sg_id, mode)
                    add_sg_ingress(client, 80, 80, 'TCP', [{'CidrIp': '0.0.0.0/0'},], [{'CidrIpv6': '::/0'},], ec2_sg_id, mode)
                    add_sg_ingress(client, 443, 443, 'TCP', [{'CidrIp': '0.0.0.0/0'},], [{'CidrIpv6': '::/0'},], ec2_sg_id, mode)

                ### ELASTIC IP ###
                ec2_elastic_ip_allocation_id = create_elastic_ip(client, 'vpc', mode)
                if ec2_elastic_ip_allocation_id:
                    ec2_elastic_ip_allocation_id = ec2_elastic_ip_allocation_id['AllocationId']

                ### EC2 INSTANCE ###
                instance = create_instance(ec2, ec2_ami, ec2_ami_type, ec2_sg_id, ec2_subnet_id, ec2_userdata, ec2_keypair_name, mode)
                if instance and instance[0]:
                    ec2_instance_id = instance[0].id
                    if ec2_instance_id:
                        instance = ec2.Instance(ec2_instance_id)
                        instance.wait_until_running(Filters=[{'Name': 'instance-id', 'Values': [ec2_instance_id,]},], DryRun=mode)

                        #### ELASTIC IP ASSOCIATION  ####
                        ec2_elastic_ip_association_id = associate_elastic_ip(client, ec2_elastic_ip_allocation_id, ec2_instance_id, mode)
                        if ec2_elastic_ip_association_id:
                            ec2_elastic_ip_association_id = ec2_elastic_ip_association_id['AssociationId']

                print('created VPC %s' % ('(dryrun)' if mode else ec2_vpc_id))
                print('created Subnet %s' % ('(dryrun)' if mode else ec2_subnet_id))
                print('created Security Group %s' % ('(dryrun)' if mode else ec2_sg_id))
                print('created Instance %s' % ('(dryrun)' if mode else ec2_instance_id))
            else:
                print('No VPCs found')
        except Exception as err:
            handle(err)
    return(0)

def info(ec2, client):
    ### KEY PAIR ###
    try:
        response = get_keypairs(client, 'key-name', ec2_keypair_name, False)
        if response and "KeyPairs" in response:
            for key in response['KeyPairs']:
                print("KeyName: %s, KeyFingerprint: %s" % (key['KeyName'], key['KeyFingerprint']))
    except Exception as err:
        handle(err)
    

#############
### MAIN ####
#############
# borrow style of https://raw.githubusercontent.com/noelmcloughlin/iot-edge-stepping-stones/master/mqtt/mqtt.py

def main(argv):
    try:
        opts, args = getopt.getopt(argv,"a:t:k:",["action=", "target=", "keypair="])
    except getopt.GetoptError as e:
        handle(e)

    ### command line arguments ###
    target="ec2"
    for opt, arg in opts:
        if opt in ("-a", "--action",):
            action = arg.lower()
        elif opt in ("-t", "--target"):
            target = arg.lower() or 'ec2'
        elif opt in ("-k", "--keypair"):
            keypair_name = arg.lower()
        else:
            usage()

    client = boto3.client('ec2', region_name=ec2_region_name)
    ec2 = boto3.resource('ec2')

    ### workflow ###
    if action == "start" and "ec2" in target:
        start(ec2, client)
    elif action in ("stop", "clean", "terminate") and "ec2" in target:
        clean(ec2, client)
    elif action == "info" and "ec2" in target:
        info(ec2, client)
    else:
        print(action)
        print(target)

if __name__ == "__main__":
   try:
       main(sys.argv[1:])
   except Exception as err:
       handle(err)
exit(0)

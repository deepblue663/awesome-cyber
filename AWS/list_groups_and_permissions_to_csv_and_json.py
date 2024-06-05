import boto3
import csv
import json
import os
from datetime import datetime
from decimal import Decimal

def get_identity_store_id():
    sso_admin_client = boto3.client('sso-admin')
    response = sso_admin_client.list_instances()
    return response['Instances'][0]['IdentityStoreId'], response['Instances'][0]['InstanceArn']

def list_groups(identity_store_id):
    identitystore_client = boto3.client('identitystore')
    paginator = identitystore_client.get_paginator('list_groups')
    groups = []

    for page in paginator.paginate(IdentityStoreId=identity_store_id):
        groups.extend(page['Groups'])
    
    return groups

def list_group_members(identity_store_id, group_id):
    identitystore_client = boto3.client('identitystore')
    paginator = identitystore_client.get_paginator('list_group_memberships')
    group_members = []

    for page in paginator.paginate(IdentityStoreId=identity_store_id, GroupId=group_id):
        group_members.extend(page['GroupMemberships'])
    
    return group_members

def get_member_name(identity_store_id, member_id):
    identitystore_client = boto3.client('identitystore')
    response = identitystore_client.describe_user(IdentityStoreId=identity_store_id, UserId=member_id['UserId'])
    return response['UserName']

def list_permission_sets(instance_arn):
    sso_admin_client = boto3.client('sso-admin')
    paginator = sso_admin_client.get_paginator('list_permission_sets')
    permission_sets = []

    for page in paginator.paginate(InstanceArn=instance_arn):
        permission_sets.extend(page['PermissionSets'])
    
    return permission_sets

def describe_permission_set(instance_arn, permission_set_arn):
    sso_admin_client = boto3.client('sso-admin')
    response = sso_admin_client.describe_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response['PermissionSet']

def list_managed_policies(instance_arn, permission_set_arn):
    sso_admin_client = boto3.client('sso-admin')
    response = sso_admin_client.list_managed_policies_in_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response['AttachedManagedPolicies']

def list_customer_managed_policies(instance_arn, permission_set_arn):
    sso_admin_client = boto3.client('sso-admin')
    response = sso_admin_client.list_customer_managed_policy_references_in_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response['CustomerManagedPolicyReferences']

def get_policy_arn_by_name(policy_name, policy_map):
    return policy_map.get(policy_name)

def describe_policy(policy_arn):
    iam_client = boto3.client('iam')
    response = iam_client.get_policy(PolicyArn=policy_arn)
    return response['Policy']

def get_policy_version(policy_arn, version_id):
    iam_client = boto3.client('iam')
    response = iam_client.get_policy_version(PolicyArn=policy_arn, VersionId=version_id)
    return response['PolicyVersion']

def get_inline_policy(instance_arn, permission_set_arn):
    sso_admin_client = boto3.client('sso-admin')
    response = sso_admin_client.get_inline_policy_for_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response.get('InlinePolicy', '')

def make_json_serializable(obj):
    """Convert non-serializable objects to serializable formats."""
    if isinstance(obj, (datetime, Decimal)):
        return str(obj)
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_serializable(i) for i in obj]
    return obj

def save_groups_and_members_to_csv(groups, identity_store_id, filename='groups_and_members.csv'):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['GroupName', 'GroupId', 'MemberId', 'MemberName'])

        for group in groups:
            group_id = group['GroupId']
            group_name = group['DisplayName']
            members = list_group_members(identity_store_id, group_id)
            if not members:
                writer.writerow([group_name, group_id, 'No members', ''])
            else:
                for member in members:
                    member_id = member['MemberId']
                    member_name = get_member_name(identity_store_id, member_id)
                    writer.writerow([group_name, group_id, member_id, member_name])

def save_permission_sets_to_csv(permission_sets, instance_arn, policy_map, filename='permission_sets.csv'):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['PermissionSetName', 'PermissionSetArn', 'Description', 'PolicyType', 'PolicyName', 'PolicyPath', 'InlinePolicyFile'])

        customer_managed_policies_details = []

        for permission_set_arn in permission_sets:
            details = describe_permission_set(instance_arn, permission_set_arn)
            managed_policies = list_managed_policies(instance_arn, permission_set_arn)
            customer_policies = list_customer_managed_policies(instance_arn, permission_set_arn)
            inline_policy = get_inline_policy(instance_arn, permission_set_arn)

            # Write managed policies
            for policy in managed_policies:
                writer.writerow([details['Name'], permission_set_arn, details.get('Description', 'No description'), 'Managed', policy['Name'], policy['Arn'], ''])

            # Collect customer-managed policies for later JSON save
            for policy_ref in customer_policies:
                policy_name = policy_ref['Name']
                policy_arn = get_policy_arn_by_name(policy_name, policy_map)
                if policy_arn:
                    policy_details = describe_policy(policy_arn)
                    policy_version = get_policy_version(policy_arn, policy_details['DefaultVersionId'])
                    policy_details['PolicyDocument'] = policy_version['Document']
                    customer_managed_policies_details.append(policy_details)
                    writer.writerow([details['Name'], permission_set_arn, details.get('Description', 'No description'), 'CustomerManaged', policy_details['PolicyName'], policy_ref['Path'], ''])

            # Write inline policy
            inline_policy_file = ''
            if inline_policy:
                inline_policy_file = f"policies/inline_policy_{permission_set_arn.split('/')[-1]}.json"
                with open(inline_policy_file, 'w') as json_file:
                    json.dump(json.loads(inline_policy), json_file, indent=4)

            writer.writerow([details['Name'], permission_set_arn, details.get('Description', 'No description'), 'Inline', '', '', inline_policy_file if inline_policy else 'No inline policy'])

    # Save customer-managed policies to JSON
    with open('policies/customer_managed_policies_details.json', 'w') as json_file:
        json.dump(make_json_serializable(customer_managed_policies_details), json_file, indent=4)

def main():
    # Create output directory for JSON files if it doesn't exist
    if not os.path.exists('policies'):
        os.makedirs('policies')

    # Get the identity store ID and instance ARN
    identity_store_id, instance_arn = get_identity_store_id()

    # List all customer-managed policies and create a mapping of policy names to ARNs
    iam_client = boto3.client('iam')
    paginator = iam_client.get_paginator('list_policies')
    policy_map = {}
    for page in paginator.paginate(Scope='Local'):
        for policy in page['Policies']:
            policy_map[policy['PolicyName']] = policy['Arn']

    # List groups and their members
    groups = list_groups(identity_store_id)
    save_groups_and_members_to_csv(groups, identity_store_id)

    # List permission sets and their policies
    permission_sets = list_permission_sets(instance_arn)
    save_permission_sets_to_csv(permission_sets, instance_arn, policy_map)

if __name__ == "__main__":
    main()
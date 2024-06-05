# AWS Identity Review
## AWS IAM Identity Center (IC) Review
To generate a report that details all Permissions Set policies as well as all Group Members we can execute the following `list_groups_and_permissions_to_csv_and_json.py` python script.  
The requirements for execution are the same as they are for [iam-identity-center-report-permissions](https://repost.aws/knowledge-center/iam-identity-center-report-permissions) AWS Community guide.  
The output of said script are the following files:  
1. groups_and_members.csv - Details about members of each group in AWS IAM IC.
2. permission_sets.csv - All permissions sets and which polices make them up.
3. policies/*.json - Details of all customer managed IAM policies which were assigned to permission sets. 
#!/bin/bash

# Set your organization ID
ORG_ID="your-organization-id"

# List all projects in the organization
projects=$(gcloud projects list --filter="parent.id=$ORG_ID" --format="value(projectId)")

# Iterate through each project and run the cloud recommender insights list command
for project in $projects; do
    echo "Processing project: $project"
    output_file="${project}_insights.json"
    
    gcloud recommender insights list \
        --insight-type=google.iam.serviceAccount.Insight \
        --project=$project \
        --location=global \
        --format=json > $output_file
        
    echo "Saved insights to $output_file"
done


#!/bin/bash

# Specify the tag key
TAG_KEY=" "   # key

# Hardcode the tag values to check
TAG_VALUES=(" ") # value

echo "Checking resources with tag key: $TAG_KEY and values: ${TAG_VALUES[@]} across all regions..."

# Get a list of all AWS regions
REGIONS=$(aws ec2 describe-regions --query 'Regions[].RegionName' --output text)

# Loop through each region
for REGION in $REGIONS; do
    echo "Checking region: $REGION"

    # Get a list of all AWS resource types that support tags in the region
    RESOURCE_TYPES=$(aws resourcegroupstaggingapi get-resources --region $REGION --output json | jq -r '.ResourceTagMappingList[].ResourceARN' | cut -d: -f3 | sort -u)

    # Loop through each resource type and check tags
    for RESOURCE_TYPE in $RESOURCE_TYPES; do
        echo "  Checking resource type: $RESOURCE_TYPE"

        # Initialize the NextToken for pagination
        NEXT_TOKEN=""

        while true; do
            # Get resources and their tags (handling pagination)
            if [ -z "$NEXT_TOKEN" ]; then
                RESPONSE=$(aws resourcegroupstaggingapi get-resources --region $REGION --resource-type-filters "$RESOURCE_TYPE" --output json)
            else
                RESPONSE=$(aws resourcegroupstaggingapi get-resources --region $REGION --resource-type-filters "$RESOURCE_TYPE" --output json --starting-token "$NEXT_TOKEN")
            fi

            # Process the resources and filter by the tag
            for TAG_VALUE in "${TAG_VALUES[@]}"; do
                echo "$RESPONSE" | jq -c --arg TAG_KEY "$TAG_KEY" --arg TAG_VALUE "$TAG_VALUE" '
                    .ResourceTagMappingList[] | 
                    select(.Tags | map(select(.Key == $TAG_KEY and .Value == $TAG_VALUE)) | length > 0) | 
                    {ResourceARN: .ResourceARN, Tags: .Tags | map(select(.Key == $TAG_KEY))}
                '
            done

            # Check if there is a NextToken for pagination
            NEXT_TOKEN=$(echo "$RESPONSE" | jq -r '.NextToken')

            # Exit the loop if there is no NextToken
            if [ "$NEXT_TOKEN" == "null" ]; then
                break
            fi
        done
    done
done

#!/bin/bash

# Config
REGION=" "   #region name
FILTER=" "   # search by name 
NEW_SNS_TOPIC_NAME=" "  # name of sns topic to ad in alarm

# Get ARN of the SNS topic
NEW_SNS_TOPIC_ARN=$(aws sns list-topics --region "$REGION" \
  --query "Topics[?contains(TopicArn, '$NEW_SNS_TOPIC_NAME')].TopicArn | [0]" \
  --output text)

if [ -z "$NEW_SNS_TOPIC_ARN" ] || [ "$NEW_SNS_TOPIC_ARN" == "None" ]; then
  echo "SNS topic '$NEW_SNS_TOPIC_NAME' not found in region '$REGION'."
  exit 1
fi

# Get all matching alarms
MATCHING_ALARMS=$(aws cloudwatch describe-alarms \
    --region "$REGION" \
    --output json | \
    jq -r --arg filter "$FILTER" '.MetricAlarms[] | select(.AlarmName | test($filter; "i")) | .AlarmName')

# Print matching alarms
echo "Matching Alarms:"
echo "$MATCHING_ALARMS"
echo ""

# Count total
TOTAL_ALARMS=$(echo "$MATCHING_ALARMS" | grep -c .)
echo "Total Alarms Found: $TOTAL_ALARMS"
echo ""

# Counter for updates
UPDATED_COUNT=0

# Loop through alarms
while IFS= read -r ALARM_NAME; do
  # Trim leading and trailing whitespace from alarm names
  ALARM_NAME=$(echo "$ALARM_NAME" | xargs)

  echo "Processing alarm: $ALARM_NAME"

  # Get current config
  ALARM_CONFIG=$(aws cloudwatch describe-alarms \
    --alarm-names "$ALARM_NAME" \
    --region "$REGION" \
    --query "MetricAlarms[0]" \
    --output json)

  if [ -z "$ALARM_CONFIG" ]; then
    echo "Could not fetch config for '$ALARM_NAME'. Skipping."
    continue
  fi

  # Check if SNS topic is already attached
  if echo "$ALARM_CONFIG" | jq -r '.AlarmActions[]?' | grep -q "$NEW_SNS_TOPIC_ARN"; then
    echo "SNS topic already attached. Skipping."
    continue
  fi

  # Add the topic and clean invalid fields
  UPDATED_ALARM_CONFIG=$(echo "$ALARM_CONFIG" | jq --arg NEW_ACTION "$NEW_SNS_TOPIC_ARN" '
    .AlarmActions += [$NEW_ACTION] |
    .AlarmActions |= unique |
    del(
      .AlarmArn,
      .StateValue,
      .StateReason,
      .StateReasonData,
      .StateUpdatedTimestamp,
      .StateTransitionedTimestamp,
      .AlarmConfigurationUpdatedTimestamp
    )')

  # Update the alarm
  aws cloudwatch put-metric-alarm \
    --region "$REGION" \
    --cli-input-json "$UPDATED_ALARM_CONFIG"

  echo "SNS topic added to '$ALARM_NAME'."
  UPDATED_COUNT=$((UPDATED_COUNT + 1))
done <<< "$MATCHING_ALARMS"

# Final summary
echo ""
echo "Done."
echo "Total Alarms Found       : $TOTAL_ALARMS"
echo "Alarms Updated with SNS  : $UPDATED_COUNT"

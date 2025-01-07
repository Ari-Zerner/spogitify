#!/bin/bash

# Export environment variables from .env file to current shell session
echo "# Run this script with 'source export-config.sh' to export variables to your shell"
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: Script must be sourced, not executed directly"
    echo "Please run: source export-config.sh"
    exit 1
fi

while IFS='=' read -r key value; do
    # Skip empty lines and comments
    if [[ -n "$key" && ! "$key" =~ ^# ]]; then
        # Remove leading/trailing quotes and whitespace from value
        value=$(echo "$value" | sed -e 's/^[[:space:]'"'"'"]*//' -e 's/[[:space:]'"'"'"]*$//')
        # Export the variable to current shell
        export "$key=$value"
    fi
done < .env
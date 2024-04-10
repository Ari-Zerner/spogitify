#!/bin/bash

# Get the absolute path of the directory containing the script
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Get the Python executable path
python_executable=$(which python3)

# Get the name of the Python script
script_name="spogitify.py"

# Set the cron schedule (e.g., every day at midnight)
cron_schedule="0 0 * * *"

# Copy environment variables to cron run environment
cron_environment="export SPOTIFY_CLIENT_ID=$SPOTIFY_CLIENT_ID; export SPOTIFY_CLIENT_SECRET=$SPOTIFY_CLIENT_SECRET"

# Set the cron command
cron_command="$cron_schedule cd $script_dir; $cron_environment; $python_executable $script_name"

# Check if the cron job already exists
if crontab -l | grep -q "$script_name"; then
    echo "Cron job for $script_name already exists. Skipping setup."
elif [ -z "$SPOTIFY_CLIENT_ID" ] || [ -z "$SPOTIFY_CLIENT_SECRET" ]; then
    echo "Spotify API credentials not found. Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables."
else
    # Add the cron job
    (crontab -l ; echo "$cron_command") | crontab -
    echo "Cron job for $script_name has been set up successfully."
fi
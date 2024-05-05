#!/bin/bash

# Get the absolute path of the directory containing the script
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Get the Python executable path
python_executable=$(which python3)

# Get the name of the Python script
script_name="spogitify.py"

# Set the cron schedule (e.g., every day at midnight)
cron_schedule="0 0 * * *"

# Set the cron command
cron_command="$cron_schedule cd $script_dir; $python_executable $script_name"

# Check if the cron job already exists
if crontab -l | grep -q "$script_name"; then
    echo "Cron job for $script_name already exists. Skipping setup."
else
    # Add the cron job
    (crontab -l ; echo "$cron_command") | crontab -
    echo "Cron job for $script_name has been set up successfully."
fi
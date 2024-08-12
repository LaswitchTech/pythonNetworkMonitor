#!/usr/bin/env python3

# System Libraries
import os
import sys
import time
import json
import argparse
import datetime
import subprocess

# SMTP Libraries
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate

# MySQL Libraries
import mysql.connector
from mysql.connector import Error

# Default configuration
default_config = {
    "db_host": "localhost",
    "db_name": "network_data",
    "db_username": "sensor_user",
    "db_password": "",
    "frequency": 60,
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_username": "user@example.com",
    "smtp_password": "",
    "recipient": "alert@example.com"
}

script_dir = os.path.dirname(os.path.abspath(__file__))
venv_path = os.path.join(script_dir, ".env/bin/activate")
config_file = os.path.join(script_dir, "config.cfg")
hosts_file = os.path.join(script_dir, "hosts.cfg")
service_name = "network_logger"

def is_service_installed():
    result = subprocess.run(['systemctl', 'list-units', '--type=service', '--all'], stdout=subprocess.PIPE)
    return f'{service_name}.service' in result.stdout.decode()

def load_config():
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
            return config
    else:
        return default_config

def save_config(config):
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)
    if args.verbose:
        print("Configuration saved.")

def configure():
    config = load_config()
    config['db_host'] = input(f"Database Host (current: {config['db_host']}): ") or config['db_host']
    config['db_name'] = input(f"Database Name (current: {config['db_name']}): ") or config['db_name']
    config['db_username'] = input(f"Database Username (current: {config['db_username']}): ") or config['db_username']
    config['db_password'] = input("Database Password: ") or config['db_password']
    config['frequency'] = int(input(f"Frequency in seconds (current: {config['frequency']}): ") or config['frequency'])
    config['smtp_host'] = input(f"SMTP Server (current: {config['smtp_host']}): ") or config['smtp_host']
    config['smtp_port'] = int(input(f"SMTP Port (current: {config['smtp_port']}): ") or config['smtp_port'])
    config['smtp_username'] = input(f"SMTP Username (current: {config['smtp_username']}): ") or config['smtp_username']
    config['smtp_password'] = input("SMTP Password: ") or config['smtp_password']
    config['recipient'] = input(f"Recipient (current: {config['recipient']}): ") or config['recipient']
    save_config(config)
    if args.verbose:
        print("Configuration saved.")

def log_error(message):
    with open(os.path.join(script_dir, 'error.log'), 'a') as f:
        f.write(f"{datetime.datetime.now()} - {message}\n")

def log_data(host, latency, config):
    try:
        connection = mysql.connector.connect(
            host=config['db_host'],
            user=config['db_username'],
            password=config['db_password'],
            database=config['db_name']
        )

        if connection.is_connected():
            cursor = connection.cursor()
            sql = "INSERT INTO readings (host, latency, timestamp) VALUES (%s, %s, NOW())"
            cursor.execute(sql, (host, latency))
            connection.commit()
            cursor.close()

    except Error as e:
        log_error(f"Database error: {e}")
        if args.verbose:
            print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Function to send an email
def send_email(subject, body, config):
    msg = MIMEMultipart()
    msg['From'] = config['smtp_username']
    msg['To'] = config['recipient']
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)  # Adding Date header

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])
        server.starttls()
        server.login(config['smtp_username'], config['smtp_password'])
        text = msg.as_string()
        server.sendmail(config['smtp_username'], config['recipient'], text)
        server.quit()
        if args.verbose:
            print("Email sent successfully!")
    except Exception as e:
        log_error(f"Failed to send email: {e}")
        if args.verbose:
            print(f"Failed to send email: {e}")

def create_service():
    service_content = f"""
    [Unit]
    Description=Network Latency Data Logger Service
    After=network.target

    [Service]
    Type=simple
    WorkingDirectory={script_dir}
    ExecStart=/bin/bash -c 'source {venv_path} && python3 {script_dir}'
    Restart=on-failure
    User={os.getlogin()}

    [Install]
    WantedBy=multi-user.target
    """
    service_file_path = f'/etc/systemd/system/{service_name}.service'

    try:
        # Write the service file using sudo
        with open(f'/tmp/{service_name}.service', 'w') as service_file:
            service_file.write(service_content)

        subprocess.run(['sudo', 'mv', f'/tmp/{service_name}.service', service_file_path], check=True)
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', f'{service_name}.service'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', f'{service_name}.service'], check=True)
        if args.verbose:
            print("Service installed, enabled and started.")
    except Exception as e:
        log_error(f"Failed to install service: {e}")
        if args.verbose:
            print(f"Failed to install service: {e}")
        sys.exit(1)

def remove_service():
    if is_service_installed():
        os.system(f'sudo systemctl stop {service_name}.service')
        os.system(f'sudo systemctl disable {service_name}.service')
        os.system(f'sudo rm /etc/systemd/system/{service_name}.service')
        os.system('sudo systemctl daemon-reload')
        if args.verbose:
            print("Service removed.")
    else:
        if args.verbose:
            print(f"Service '{service_name}.service' is not installed.")

def start_service():
    if is_service_installed():
        subprocess.run(['sudo', 'systemctl', 'start', f'{service_name}.service'])
        if args.verbose:
            print("Service started.")
    else:
        if args.verbose:
            print(f"Service '{service_name}.service' is not installed.")

def stop_service():
    if is_service_installed():
        subprocess.run(['sudo', 'systemctl', 'stop', f'{service_name}.service'])
        if args.verbose:
            print("Service stopped.")
    else:
        if args.verbose:
            print(f"Service '{service_name}.service' is not installed.")

# Function to load hosts from the config file
def load_hosts():
    if os.path.exists(hosts_file):
        with open(hosts_file, 'r') as file:
            return json.load(file)
    else:
        log_error(f"Could not open the hosts file: {hosts_file}")
        if args.verbose:
            print(f"Could not open the hosts file: {hosts_file}")
        return []

# Function to check if a host is up and return the latency
def ping_host(host):
    try:
        result = subprocess.run(['ping', '-c', '1', host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            latency = float(result.stdout.decode().split('time=')[-1].split(' ms')[0])
            return latency
        else:
            return None
    except Exception as e:
        log_error(f"Failed to ping {host}: {e}")
        if args.verbose:
            print(f"Failed to ping {host}: {e}")
        return None

def add_host(new_host):
    hosts = load_hosts()
    if new_host in hosts:
        log_error(f"Host {new_host} is already in the list.")
        if args.verbose:
            print(f"Host {new_host} is already in the list.")
    else:
        hosts[new_host] = {"recipient": default_config['recipient']}
        with open(hosts_file, 'w') as file:
            json.dump(hosts, file, indent=4)
        if args.verbose:
            print(f"Host {new_host} added.")

def remove_host(host_to_remove):
    hosts = load_hosts()
    if host_to_remove in hosts:
        del hosts[host_to_remove]
        with open(hosts_file, 'w') as file:
            json.dump(hosts, file, indent=4)
        if args.verbose:
            print(f"Host {host_to_remove} removed.")
    else:
        log_error(f"Host {host_to_remove} not found.")
        if args.verbose:
            print(f"Host {host_to_remove} not found.")

if __name__ == "__main__":
    script_name = sys.argv[0]

    parser = argparse.ArgumentParser(
        description="Network Latency Data Logger",
        epilog=f"Examples:\n"
               f"  python3 {script_name} --once --verbose\n"
               f"  python3 {script_name} --console\n"
               f"  python3 {script_name} --once --console --verbose\n"
               f"  python3 {script_name}\n\n"
               "The script allows you to:\n"
               "- add a host with --add [host]\n"
               "- remove a host with --remove [host]\n"
               "- Run continuously or take a single reading with --once\n"
               "- Print the readings without storing them using --console\n"
               "- Print the readings to the console with --verbose\n"
               "- Install the script as a service with --install\n"
               "- Uninstall the service with --uninstall\n"
               "- start the service with --start\n"
               "- stop the service with --stop\n"
               "- Configure the script with --configure",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("--once", action="store_true", help="Retrieve and store the sensor data only once.")
    parser.add_argument("--console", action="store_true", help="Only display the sensor data without storing it.")
    parser.add_argument("--verbose", action="store_true", help="Echo the sensor readings to the console.")
    parser.add_argument("--install", action="store_true", help="Install the script as a systemd service.")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall the script as a systemd service.")
    parser.add_argument("--configure", action="store_true", help="Configure the script settings.")
    parser.add_argument("--start", action="store_true", help="Start the service if installed.")
    parser.add_argument("--stop", action="store_true", help="Stop the service if installed.")
    parser.add_argument("--add", metavar="HOST", help="Add a host to the monitoring list.")
    parser.add_argument("--remove", metavar="HOST", help="Remove a host from the monitoring list.")

    args = parser.parse_args()

    if args.configure:
        configure()
    else:
        config = load_config()

        if args.install:
            create_service()
        elif args.uninstall:
            remove_service()
        elif args.start:
            start_service()
        elif args.stop:
            stop_service()
        elif args.add:
            add_host(args.add)
        elif args.remove:
            remove_host(args.remove)
        else:
            try:
                def process_monitor():
                    hosts = load_hosts()
                    if not hosts:
                        log_error(f"No hosts to monitor. Please check hosts.cfg.")
                        if args.verbose:
                            print("No hosts to monitor. Please check hosts.cfg.")
                        return
                    for host in hosts:
                        if args.verbose:
                            print(f"Checking host: {host}")
                        latency = ping_host(host)
                        if latency is not None:
                            if args.verbose:
                                print(f"Host {host} is up with latency {latency} ms")
                            if not args.console:
                                log_data(host, latency)
                        else:
                            if args.verbose or not args.console:
                                print(f"Host {host} is down!")
                            if not args.console:
                                send_email(f"Host {host} is down!", f"The host {host} is not responding to ICMP requests.", hosts[host]['recipient'])

                if args.once:
                    process_monitor()
                    if args.verbose:
                        print("Completed a single round of monitoring.")
                else:
                    if config['frequency'] < 5:
                        log_error(f"Frequency too low ({config['frequency']}s). Setting to minimum value of 5s.")
                        if args.verbose:
                            print(f"Frequency too low ({config['frequency']}s). Setting to minimum value of 5s.")
                        config['frequency'] = 5
                    while True:
                        process_monitor()
                        time.sleep(config['frequency'])
            except KeyboardInterrupt:
                if args.verbose:
                    print("\nStopping...")

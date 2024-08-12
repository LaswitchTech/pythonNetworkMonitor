#!/bin/bash

# Function to check if MariaDB is installed
is_mariadb_installed() {
  if dpkg -l | grep -q mariadb-server; then
    echo "MariaDB is already installed."
    return 0
  else
    return 1
  fi
}

# Function to check if the database and table exist
is_database_configured() {
  DB_EXISTS=$(sudo mariadb -u root -e "SHOW DATABASES LIKE 'network_data';" | grep "network_data" > /dev/null; echo "$?")
  if [ "$DB_EXISTS" -eq 0 ]; then
    echo "Database 'network_data' already exists."
    TABLE_EXISTS=$(sudo mariadb -u root -e "USE network_data; SHOW TABLES LIKE 'readings';" | grep "readings" > /dev/null; echo "$?")
    if [ "$TABLE_EXISTS" -eq 0 ]; then
      echo "Table 'readings' already exists."
      return 0
    else
      return 1
    fi
  else
    return 1
  fi
}

# Function to check if the configuration file exists
is_config_exists() {
  config_file="config.cfg"
  if [ -f "${config_file}" ]; then
    echo "Configuration file already exists."
    return 0
  else
    return 1
  fi
}

# Function to prompt the user for MariaDB installation
prompt_mariadb_installation() {
  if ! is_mariadb_installed; then
    read -p "Do you want to install MariaDB on this Raspberry Pi? (y/n): " install_mariadb
    echo
  else
    install_mariadb="n"
  fi
}

# Function to prompt the user for the MariaDB password
prompt_mariadb_password() {
  read -sp "Please specify the password to be used for the MariaDB user 'monitor_user': " password_mariadb
  echo
}

# Function to prompt the user for SMTP configuration
prompt_smtp_configuration() {
  if ! is_config_exists; then
    read -p "Please specify the SMTP server (default: smtp.example.com): " smtp_host
    smtp_host=${smtp_host:-"smtp.example.com"}

    read -p "Please specify the SMTP port (default: 587): " smtp_port
    smtp_port=${smtp_port:-587}

    read -p "Please specify the SMTP username: " smtp_username
    read -sp "Please specify the SMTP password: " smtp_password
    echo

    read -p "Please specify the email address to send alerts to: " recipient
  fi
}

# Function to update the system
update_system() {
  echo "Updating the system..."
  sudo apt-get update && sudo apt-get upgrade -y
  if [[ $? -ne 0 ]]; then
    echo "System update failed. Exiting."
    exit 1
  fi
  echo "System update completed."
}

# Function to install dependencies
install_dependencies() {
  echo "Installing dependencies..."
  sudo apt-get install -y git python3 python3-pip mariadb-client
  if [[ $? -ne 0 ]]; then
    echo "Failed to install dependencies. Exiting."
    exit 1
  fi
}

# Function to install MariaDB
install_mariadb() {
  if ! is_mariadb_installed; then
    sudo apt-get install -y mariadb-server
    sudo mysql_secure_installation
  else
    echo "Skipping MariaDB installation as it is already installed."
  fi

  # Automate database setup if it doesn't exist
  if ! is_database_configured; then
    sudo mariadb -u root <<EOF
CREATE DATABASE network_data;
CREATE USER 'monitor_user'@'localhost' IDENTIFIED BY '$password_mariadb';
GRANT ALL PRIVILEGES ON network_data.* TO 'monitor_user'@'localhost';
FLUSH PRIVILEGES;
USE network_data;
CREATE TABLE readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    host VARCHAR(255) NOT NULL,
    latency FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF
    sudo systemctl enable mariadb
    echo "Database and table created successfully."
  else
    echo "Skipping database and table creation as they already exist."
  fi
}

# Function to create the configuration file
create_config_file() {
  config_file="config.cfg"
  if [ ! -f "$config_file" ]; then
    echo "Creating configuration file: $config_file"
    cat <<EOF > $config_file
{
    "db_host": "localhost",
    "db_name": "network_data",
    "db_username": "monitor_user",
    "db_password": "$password_mariadb",
    "frequency": 60,
    "smtp_host": "$smtp_host",
    "smtp_port": $smtp_port,
    "smtp_username": "$smtp_username",
    "smtp_password": "$smtp_password",
    "recipient": "$recipient"
}
EOF
    echo "Configuration file created."
  else
    echo "Configuration file already exists."
  fi
}

# Main script execution
update_system
install_dependencies
prompt_mariadb_installation
prompt_mariadb_password
prompt_smtp_configuration
create_config_file

if [ "$install_mariadb" == "y" ]; then
  install_mariadb
  echo "MariaDB installation and configuration completed."
else
  echo "Skipping MariaDB installation."
fi

echo "Installation process completed."

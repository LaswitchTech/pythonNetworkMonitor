# Usage
To use the script, the virtual environment must be loaded. A ``run.sh`` bash wrapper is included.
## Help Message
```
$ ./run.sh --help
usage: monitor.py [-h] [--once] [--console] [--verbose] [--install] [--uninstall] [--configure] [--start] [--stop] [--add HOST] [--remove HOST]

Network Latency Data Logger

options:
  -h, --help     show this help message and exit
  --once         Retrieve and store the sensor data only once.
  --console      Only display the sensor data without storing it.
  --verbose      Echo the sensor readings to the console.
  --install      Install the script as a systemd service.
  --uninstall    Uninstall the script as a systemd service.
  --configure    Configure the script settings.
  --start        Start the service if installed.
  --stop         Stop the service if installed.
  --add HOST     Add a host to the monitoring list.
  --remove HOST  Remove a host from the monitoring list.

Examples:
  python3 monitor.py --once --verbose
  python3 monitor.py --console
  python3 monitor.py --once --console --verbose
  python3 monitor.py

The script allows you to:
- add a host with --add [host]
- remove a host with --remove [host]
- Run continuously or take a single reading with --once
- Print the readings without storing them using --console
- Print the readings to the console with --verbose
- Install the script as a service with --install
- Uninstall the service with --uninstall
- start the service with --start
- stop the service with --stop
- Configure the script with --configure
```

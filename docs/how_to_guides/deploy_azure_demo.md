# Deploying Demo Instance to Azure

These instructions are a quick reference for deploying a non-production demo instance of QCrBox to the Azure cloud platform as a virtual machine. They are designed to replicate the instance used for demonstrating QCrBox at various conferences and meetings.

!!! info inline end
    Note that these instructions are not sufficient for a production deployment!
    When the demo virtual machine is not in use, it is strongly recommended to shut down the instance.
    For a production deployment, ensure that appropriate production-level measures are taken to secure the instance and its services, with the infrastructure provided via a suitably configured web server over HTTPS

!!! info inline end
    These instructions will need to be reviewed and updated following the planned reintroduction of Traefik

Prerequisites
- Prior experience in setting up a Microsoft Azure resource group
- Prior experience in installing and configuring QCrBox backend and frontend
- A Microsoft Azure account (this guide has been tested with a subscription under an Enterprise account)
- A local machine with the Azure CLI client installed and configured for access to the Azure account resources

## Azure Resources Creation and Configuration

### Instance VM

First create a Resource Group if one does not already exist (e.g. `qcrbox-demo_group`),
then create a virtual machine for QCrBox, with the following parameters in each section:

**Basics:**

```
- Project details:
  - Resource group: qcrbox-demo-group
- Instance details:
  - Virtual machine name: qcrbox-demo
  - Region: (UK) UK South
  - Zone options: select 'Azure-selected zone (Preview)'
  - Security type: Standard
  - Image: Ubuntu Server 24.02 LTS - x64 Gen2
  - VM architecture: x64
  - Run with Azure Spot discount: Disabled
  - Size: Standard_B4ms - 4 vcpus, 16 GiB memory
  - Enable Hibernation: Disabled
- Administrator account
  - Authentication type: SSH public key
  - Username: qcrbox
  - SSH public key source: Generate new key pair
  - SSH key type: RSA SSH Format
  - Key pair name: qcrbox-demo_key
- Inbound port rules:
  - Public inbound ports: Allow selected ports
  - Select inbound ports: SSH (22)
```

**Disks:**

```
- Encryption at host: Disabled
- OS disk:
  - OS disk size: 60 GiB [?]
  - OS disk type: Premium SSD (locally redundant storage)
  - Delete with VM: Enabled
  - Key management: Platform-managed key
  - Enable Ultra Disk compatibility: Disabled
- Data disks for qcrbox-demo: None
```

**Networking:**

```
- Virtual network: Select `Create new` with the following settings:
  - Name: qcrbox-demo-vnet
  - Address space: use default settings, e.g.
    - Address range: 10.1.0.0/16
    - Addresses 10.1.0.0 - 10.1.255.255 (65536 addresses)
    - Overlap: None
  - Subnets: use default settings, e.g.
    - Subnet name: default
    - Address range: 10.1.0.0/24
    - Addresses: 10.1.0.0 - 10.1.0.255 (256 addresses)
- Subnet: default (10.0.0.0/24)
- Public IP: use selected default of 'Create new' with the following settings:
  - Name: qcrbox-demo-ip
  - SKU: Standard
  - Assignment: Static
  - Routing preference: Microsoft Network
  - Availability zone: Azure-selected zone
- NIC network security group: Basic
- Public inbound ports: Allow selected ports
- Delete public IP and NIC when VM is deleted: Enabled
- Enable accelerated networking: Disabled
- Load balancing options: None
```

**For the Management, Monitoring and Advanced sections, use the supplied defaults**

Finally, select `Create` to create the instance.

### Configure VM Network Security Group

This enables the correct HTTP/S and QCrBox ports to be accessible from the internet.

1. Select the created `qcrbox-demo-nsg` resource, and then `Settings` on the left navigation bar
1. Add the following new rules under `Inbound security rules`:
   - Standard HTTP (port 80) and HTTPS (port 443) rules
   - Custom rules for the following destination ports, all with `Protocol: Any`, `Source: Any`, `Source port ranges: *`, `Destination: Any`, `Action: Allow`
     - 11000, 12003, 12004, 12006, 12008
1. Select `Save`

## Docker Installation and QCrBox Deployment

After starting the instance and connecting to the instance's `qcrbox` account via SSH or an Azure console,
set up a directory to store the install scripts for Docker and QCrBox, e.g.:

```bash
cd ~
mkdir scripts
cd scripts
```

Download and install Docker:

```bash
curl -fsSL https://get.docker.com -o install-docker.sh
sh install-docker.sh --dry-run
sudo sh install-docker.sh
sudo usermod -aG docker $USER
```

Also into the `scripts` directory, download and install QCrBox:

```bash
curl -fsSL https://raw.githubusercontent.com/QCrBox/QCrBox/dev/scripts/qcrbox_setup.sh > qcrbox_setup.sh
cd ~
bash scripts/qcrbox_setup.sh
```

Following the instructions given when running the `qcrbox_setup.sh` script, and then activate a Devbox shell to complete the installation:

```bash
cd QCrBox
devbox shell
```

## Download Third Party Distributables

This currently consists of obtaining the MoPro application distributable `MoProSuite_win_2022_07.zip`, following the [instructions](../how_to_guides/obtain_licenced_components.md),
and moving it into the MoPro services directory, e.g.:

```bash
mv MoProSuite_win_2022_07.zip ~/QCrBox/services/applications/mopro/
```

## Configure `qcrbox_quality` Service

For Azure deployment, we also need to add the host public IP to Django's `ALLOWED_HOSTS` configuration setting for the `qcrbox_quality service`. Add `ENV ALLOWED_HOSTS="<public_ip_address>"` to `services/applications/qcrbox_quality/Dockerfile`.

## Build and Start all Services

```bash
qcb build --all
qcb up --all
```

## Final Service Configuration

### Logs Configuration

Once started, create a symbolic link to the QCrBox logs for convenience:

```bash
ln -s ~/QCrBox/services/core/qcrbox_syslog/logs logs
```

### Configure Automated Logrotation

Add the following as a new file `/etc/logrotate.d/qcrbox`:

```
/etc/logrotate.d/qcrbox:

/home/qcrbox/QCrBox/services/core/qcrbox_syslog/logs/*.log {
        daily
        rotate 7
        missingok
        notifempty
        copytruncate
}
```

Then test the logrotation:

```bash
cd /etc/logrotate.d
sudo logrotate -f qcrbox
```

Ensure the log file names in the `logs` directory have correct rotation suffixes.

## Convenient Restart Script

For a conveniently located script to restart all services:

```bash
cp ~/QCrBox/scripts/restart_qcrbox.sh ~/scripts/restart-qcrbox-backend.sh
```

Edit `~/scripts/restart-qcrbox-backend.sh` and amend `qcrbox --all` to include only those services you wish to bring up for any demo (for efficiency). For example, edit the line to read:

```bash
qcb up olex2 crystal-explorer qcrbox_quality mopro
```

## Install and Configure Front-end

```bash
git clone https://github.com/QCrBox/QCrBoxFrontend
cd QCrBoxFrontend
cp environment.env.template environment.env
```

Edit `environment.env` to include the needed username and password settings,
then start the front-end:

```bash
docker compose build
docker compose up -d
```

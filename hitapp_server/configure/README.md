# Configuration

## Overview
This lets you configure the repo for offline use or revert it back to online. 

## Pip Install

Install the following libraries using pip:
```bash
pip install pyyaml
```

## Offline configuration

1. Run the following command: `python configure.py --config configs/offline.yaml`
2. Copy the any additional files you need to the static folder.

## Online configuration
1. Run the following command: `python configure.py --config configs/online.yaml`

## Offline Docker Setup
1. If you are want to use it offline, save the images you built in the previous step with the following command:
    ```bash    
    docker save -o hitapp_server-api.tar hitapp_server-api:latest
    docker save -o hitapp_server-frontend.tar hitapp_server-frontend:latest
    docker save -o postgres.tar postgres:14-alpine
    ```
1. Then copy the entire repo and the docker images to the offline machine.

1. On the offline machine run the following commands (use the docker-compose-offline.yml file):
    ```bash
    docker load -i hitapp_server-api.tar
    docker load -i hitapp_server-frontend.tar
    docker load -i postgres.tar
    docker-compose up -d
    ```
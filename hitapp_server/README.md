# HITTApp Server

This application provides back-end for external crowdsourcing job. 
A typical Amazon Mechanical Turk (AMT) task can be deployed in this server; participants answers will be stored
in the dataset, and can be downloaded. 
YOu can deploy the server on a Linux Virtual Machine. 

## Get started 

The following steps should be performed to prepare the system locally. Similarly it can be deployed on a VM.


1. Install `docker` and `docker-compose`, if they are not already installed. Follow the platform specific installation instructions.

1. The server is published as a part of P.910 Toolkit. Clone or download the repository from Github: https://github.com/microsoft/P.910, e.g.

    ```bash
    git clone https://github.com/microsoft/P.910
    cd P.910/hitapp_server
    ```

1. Copy `.env.template` to a new file, name it `.env` put it in the root directory of this project. 
Then change the passwords inside your `.env` file:  

    ```INI
    POSTGRES_PASSWORD=[Your_password]
    APP_DB_PASS=[Your_password]
    ```

1. Run the docker-compose

    ```bash    
    docker-compose up --build -d
    ```
    
1. Checkout the system on [localhost](http://localhost).
    Use "admin" as username and "hitapp" as password to access the platform. 
    
    It is recommended to change the password,
    by editing the `front-end/.htpasswd`. You can use _openssl_ to create a new encoded password:
    ```bash    
    openssl passwd -crypt PASSWORD
    ```
    Then change the `front-end/.htpasswd` file to:
    ```INI    
    admin:YOUR_NEW_ENCODED_PASSWORD
    ```
    


## Stop the system

1. In case you want to stop the services use:

    ```bash    
    docker-compose down
    ```
    or  following command when the data-storage should be cleaned
    
    ```bash    
    docker-compose down --volumes
    ```
    
    
## Deploying on cloud server


1. Create a Linux Virtual Machine (VM)
    
    1. Add a DNS name, so you have a URL for your VM
    1. Make sure that port 80 is open
    
1. Connect to the VM through SSH

1. Follow the rest of procedure given in the "Get started" section 


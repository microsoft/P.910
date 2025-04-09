[Home](../README.md) > Preparation
# Preparation

The following steps should be performed to prepare the test setup.

1. Install `python` and `pip`, if they are not already installed. Follow the platform specific installation instructions.

1. Clone or download the P.910-crowd Toolkit repository from Github: https://github.com/microsoft/P.910, e.g.

    ```bash
    git clone https://github.com/microsoft/P.910
    cd P.910
    ```

1. Install the python module dependencies in `requirements.txt` using `pip`

    ```bash
    cd src
    pip install -r requirements.txt
    ```
    
1. (optional) Upload the general resources (found in `src\template\assets\imgs`) in a cloud server and change the 
URLs associated to them as described in [General Resources](general_res.md)

1. Install the [HITAPP Server](..//hitapp_server) on a linux based Virtual Machine with a domain name.
You may use [Azure Virtual Machine](https://azure.microsoft.com/en-us/services/virtual-machines/) or any other cloud services. 
 
     **Note**: Currently Amazon Mechanical Turk do not support fulls-screen video playback. Therefore, using the **HITAPP Server**
      project is necessary. 

1.  Follow the rest of preparation process based on the test methodology you want to apply:    
    - [Preparation for Absolute Category Rating (ACR) and ACR-HR](prep_acr.md)
    - [Preparation for Degradation Category Rating (DCR) and Comparison Category Rating (CCR)](prep_dcr.md)
    - [Preparation for Photorealistic Avatars evaluation](prep_avatar.md)

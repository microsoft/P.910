[Home](../README.md) > Running the Crowdsourcing Test

# Running the Crowdsourcing Test 

Following steps explain how to conduct a subjective video quality test on a crowdsourcing platform (here we use Amazon
Mechanical Turk  AMT as an example). 
It is required to perform the [preparation](preparation.md) step first. 
As a result you should have a directory named YOUR_PROJECT_NAME which contains:
 
   * `YOUR_PROJECT_NAME_dcr.html`: Customized HIT app to be used in AMT.
   * `YOUR_PROJECT_NAME_publish_batch.csv`: List of dynamic content to be used during publishing batch in AMT.
   * `YOUR_PROJECT_NAME_dcr_result_parser.cfg`: Customized configuration file to be used by `result_parser.py` script    
    
You will use the first two files in this part. We will create the test on the HIT APP server and use AMT to direct crowd workers to the test.
The workflow from crowd worker's perspective is as following:
-  A crowdworker see a HIT which is an advertisement for the test. It contains a link to a HIT App and a text field.
-  By following the link, the crowdworker will participate in a viewing session.
-  At the end of session and by submitting their answers, participant get a verification code.
-  Participant should copy this code and paste it in the text field from AMT hit. We will use this code later to find out
which participant should be Accepted/rejected or get bonuses.    


## Create the test on HITAPP Server
Get your [HITApp Server](../hitapp_server/README.md) started and follow next steps to publish your HIT App
on that:

1. Use a web browser and open your website. Login with the username and password your set (or default one) and go to "**New Project**".

1. Fill in the form and upload `YOUR_PROJECT_NAME_dcr.html` as HTML file, and `YOUR_PROJECT_NAME_publish_batch.csv` as CSF file. Finally click on **Submit**.

    **Note:** The _Number of assignment per HIT_ refers to the target number of participants. Here it only be used to provide statistics on the number of submitted answers.


1. Now your HIT App will be created. As soon as the process is finished, you will see **AMT resources** links for download in the **Project Status** page. 
Download the _AMT HIT_ and _AMT Input File_ and follow to the next section on how to create the HIT in AMT. 

    **Note:** You can download your answers later from the same page. 


## Create the test on AMT
The HIT in AMT is actually a simple form which provide basic information about the test, a link to a HIT from the test and a text field in which participants 
should past the verification code they get from HIT App Server.

1. Create [an account on AMT](https://requester.mturk.com/create/projects/new)

1. Create a New Project for your test
  
    1. Go to “**Create**” > “**New Project**” > “**Survey Link**” > “**Create project**”

    1. Fill information in “**1 – Enter Properties**”, important ones: 

	    * **Setting up your survey**
            * **Reward per response**: It is recommended to pay more than the minimum wage of target country per hour. 
            * **Number of respondents**: It is the number of votes that you want to collect per clip.
            * **Time allotted per Worker**: 1 Hour
	    * **Worker requirements**
            * **Add another criterion**: **HIT Approval Rate(%)** greater than 98
            * **Add another criterion**: **Number of HITs Approved** greater than 500
            * **Location**: It is required that workers are native speakers of the language under study

    1. Save and go to “**2 – Design Layout**”:
   
        1. Click on **Source**
        
        1. Copy and paste the content of `AMT HIT` here.
      
        1. Click on **Source**, then **Save**

### Create a _New Batch with Existing Project_ - using website

1. Go to “**Create**” > “**New Batch with an Existing Project**”, find your project and click on "**Publish Batch**" 

1. Upload your csv file `AMT Input File`).

1. Check the HITs and publish them.

1. Later, download the results from “**Manage**” > “**YOUR_BATCH_NAME**” > “**Review Results**” > “**Download CSV**”.
 

# treeherder-demo-client

##Introduction
[Treeherder](https://treeherder.mozilla.org) is a reporting dashboard for that allows users to see the results of automatic or manual builds from Mozilla checkins and their respective tests. <br>

The purpose of this tool is to enable the submission of a generic job run result from a machine(local PC/Mac/Jenkins machine) to an instance of Treeherder. This project contains set of scripts that can be customized or extended as per the needs of your implementation. 

There are essentially three kinds of instances of Treeherder to which you can submit data -<br>
1. Local (http://local.treeherder.mozilla.org) - This is when you download or fork the treeherder repository and start an instance on your PC/Mac/local machine. This is usually done to set up a local sandbox for testing purposes.<br>
2. Staging (https://treeherder.allizom.org) - This is a publicly available continuously running server maintained by the treeherder team which is used for pre-deployment tests. <br>
3. Production (https://treeherder.mozilla.org) - This is the publicly available production instance of treeherder against which you can only submit pre-tested legitimate test run results. <br>

By default the ```treeherder-demo-client``` tool submits to the Local Treeherder instance, but you can direct the output to any Treeherder instance with these params=><br> ```--treeherder-url=<Fill> --treeherder-client-id=<Fill> --treeherder-secret=<Fill>```


##Requirements
It is assumed that you already have a Linux based development environment setup (eg:- Tool was developed on Mac OS X Yosemite). Posting to treeherder can be done via a treeherder python client or a node.js client; this tool only uses the python client. It is assumed that your development environment already has python 2.7.9+ already installed (2.7.9+ is required for authentication).

If you are planning on submitting data to a local instance(a must if you are testing) [Virtual Box] (https://www.virtualbox.org/) and [Vagrant](https://www.vagrantup.com/) are also required for the development environment. If you don’t have them installed, please refer to the hyperlinks on how to install them.

Note - If your submissions need to work, they will need the treeherder client module. Install this using =>

	pip install treeherder-client
	#Supporting packages
	pip install mozinfo boto
If you are installing the complete Treeherder package anyways to run a local instance, then treeherder-client gets installed as a part of it.


##Quickstart
The below steps will create a local instance of Treeherder, run a sample test script and log the result using the submission script. <br>
1. git clone https://github.com/RitheshShenthar/treeherder-demo-client.git<br>
2. [Install a local instance of Treeherder](http://treeherder.readthedocs.org/installation.html) . Verify that ```http://local.treeherder.mozilla.org/``` is up and running and that it is ingesting pulse data i.e Treeherder is acquiring information about Mozilla checkins with revision ids.<br>
3. Create Hawk credentials using the following commands (after starting Treeherder as in Step (2)) 

	~/treeherder$ vagrant ssh
	vagrant ~/treeherder $ ./manage.py create_credentials test-client-id treeherder@mozilla.com "Description"

4.Find a valid revision id against which we can submit a test result. To do this, look for a revision id that is already ingested in your local treeherder under repo "mozilla-inbound". (Since the default repo in our project is mozilla-inbound). eg:- f5f9a967030d

![alt tag](https://github.com/RitheshShenthar/submit-to-th/blob/master/Treeherder.png?raw=true)

5.Under the ```treeherder-demo-client```  folder, run the below command provided with =><br>
1) valid revision id for repository "mozilla-inbound" using ```--revision```. <br>
2) valid secret key obtained as output in step (3)


	./submission.py --repository=mozilla-inbound --test-type=functional --revision [FILL] --treeherder-url=http://local.treeherder.mozilla.org/ --treeherder-client-id=test-client-id --treeherder-secret=[FILL] --build-state=running treeherder_venv
	

6.Under the ```treeherder-demo-client``` folder, run ```./dummyTest```<br>
7.Run the same command as in step (5) except with ```--build-state=completed```<br>
8.Navigate to Treeherder UI and verify that result was logged. (Ensure that the correct Tier is selected as necessary in the dropdown.)

<em>Important</em> - <br>1. For the benefit of the user, the demo client has a pre-uploaded sample S3 log which we submit to Treeherder(as seen in ```config.py```'s ```log_reference``` field.<br> ```'log_reference': 'https://s3-us-west-1.amazonaws.com/services-qa-jenkins-artifacts/jobs/dummy-test/7/log_info.txt'```<br>
2. In the real world, the user would need to publish the ``log_info.txt`` created by the dummyTest/actual job and to an S3 bucket or equivalent, and then pass that reference to Treeherder using the same ```log_reference``` field.)<br>
3. You will see the sample log file under Fail

##Extending the tool

Treeherder provides a library, called ```treeherder-client```, to support data submission to a treeherder service instance. The ```treeherder-demo-client``` project internally uses this module to execute submissions.
Before you can submit data to treeherder, you will need at least this much information-<br>
1. Hawk credentials - Whether you are using a Local/Staging/Production Treeherder instance, you will need to [acquire API credentials](https://treeherder.readthedocs.org/common_tasks.html#managing-api-credentials) in order to authenticate your submissions. <br><b>Note-</b> For local instances, you can use the command in the link only once Treeherder instance is up. Also you will need to recreate the credentials every time you destroy and recreate the local instance.<br>
2. repository - you will need to know which repository you want to log results against.<br>
3. revision - you will need to know which revision of the above repository you want to log results against.<br>
4. test-type - Know what types of tests are permitted by config.py.<br>
5. config.py - Have appropriate configurations placed here. The submission to treeherder is constructed as a "job" with information that is placed here.
 
 This tool can be customized to submit the results of any kind of job and any kind of repository. It contains python code that can help you submit data to Treeherder from any linux based machine. It also accepts a ```log_reference``` field in ```config.py``` which should contain the link to a pre-published S3 Log or similar. 
 
 	./submission.py --repository=[mozilla-inbound] --test-type=[functional] --revision [FILL] --treeherder-url=[http://local.treeherder.mozilla.org/] --treeherder-client-id=[FILL] --treeherder-secret=[FILL] --build-state={running|completed}   treeherder_venv

<b>Customization </b>

1. <b>Script modifications-</b> You can modify settings to suit your project and submit a job to indicate that the job is running -<br>
a. Script commandline params need to be modified as per your project- eg:-submission.py --repository=xxxx<br>
b. config.py - Settings in the config.py need to be modified to suit your project and job. See config.py for details.<br>
c. You can add os environment variables with the below names or optionally pass them in the commandline. 

		TREEHERDER_CLIENT_ID
		TREEHERDER_URL
		TREEHERDER_SECRET
	
	
2. <b>Compatible Tests/Jobs-</b>
The criteria for writing compatible tests or jobs are-<br>
a.The job needs to create a simple file called ```retval.txt``` and store a "0" (on PASS) or "1" (on FAIL) in it and <b>nothing else</b>.  <br>Eg:- If a job has 100 tests and 1 has failed, the job should create a file ```retval.txt``` and in it store a job result of "1" indicating the failure and save only that integer in the file as a string(see ```dummyTest``` for reference)<br>
b. All logging needs to be done into a file called ```log_info.txt```.<br>
c. Both files need to be stored in the same folder/workspace as the ```treeherder-demo-client```<br>

3. <b>JENKINS</b> - If running on a Jenkins machine, modify submission.py by opening the file and following the instructions under # IF USING JENKINS.

##Stepwise submission process
<b>Step 1</b><br>
Run the script commandline ./submission.py with ```--build-state=running``` in the CLI command.<br>
<b>Step 2</b><br>
Whatever job/test suite needs to be run, is run.(eg:-```./dummyTest``` in our case)<br>
<b>Step 3</b> <br>
Run the script commandline ./submission.py with ```--build-state=completed``` in the CLI command.<br>
<b> Step 4</b><br>
Verify that results are popping up on treeherder. Ensure correct Tier is checked in the Dropdown.

#Troubleshooting
Useful logs for debugging.

	/var/log/gunicorn/treeherder_error.log

	vagrant /var/log/treeherder $ ls
	treeherder.log  treeherder.log.1  treeherder.log.2
Or in the vagrant SSH when starting up the treeherder instance just do:
	
	vagrant ~/treeherder $ ./bin/run_gunicorn | grep error

#Known issues
1. If your Local Treeherder instance is not ingesting tasks, go to your ```treeherder``` directory and execute the following -<br>
a. ```vagrant destroy```<br>
b. ```rm -rf celerybeat-schedule``` <br> 
c. and restart the build process.<br>

2. If submitting to the local treeherder instance was working great, but submitting to the live treeherder staging from jenkins fails with the following error:
```13:50:05 requests.exceptions.HTTPError: 403 Client Error: FORBIDDEN for url```
This indicates that the jenkins node time is off from the treeherder server time by more than 60 seconds, and authentication will fail; so be sure that your jenkins server time is correct.

3. If you are running Ubuntu and are having issues bringing up the Local instance, try <br>a.```sudo apt-get install nfs-kernel-server```<br>b. Rebuild the local virtualbox (```sudo /etc/init.d/vboxdrv setup)```<br>
	
#Note:
If you want to further understand Treeherder and how to install it locally, please read these docs -<br>
 https://wiki.mozilla.org/EngineeringProductivity/Projects/Treeherder<br>
 http://treeherder.readthedocs.org/installation.html<br>
 Want to learn more or have any specific questions? Chat on IRC:#treeherder<br>
 
 If you want to see examples of Jenkins to Treeherder submissions, see the following links-<br>
 http://robwood.zone/posting-to-treeherder-from-jenkins/<br>
 https://github.com/mozilla/mozmill-ci/blob/master/jenkins-master/jobs/scripts/workspace/submission.py<br>
 
 
 
  







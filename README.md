# Gmail-Based-Build-Server
A build server based on gmail. Check emails for pending build jobs. Build. Then reply with the output.

This work is inspired by a personal experience of running code for my girlfriend. She is taking a data science course in college, which has lots of coding assignments. Most of the assignments are highly computing intensive, and her laptop is too slow to run those programs. My laptop is quite powerful, it has a quad core 2.6 GHz Core i7 CPU, those programs run a lot faster on my laptop. But it's inconvenient for her to ask me for help every time, given that I am not always at home, and we have 3 hours time difference. Therefore, I build this Build Server based on Gmail, which can run all day long on my laptop. She can just send the build job to my gmail, then the server will automatically fetch the code and data, build the job, and return necessary outputs to her email. In this way, she can always have access to the computing resources on my laptop, and also I don't need to manually run the code for her every time.

Currently, this build server only works for python jobs, but it's quite easy to extend the scope to any kind of jobs. The only requirements to run this build server is Python, and [Gmail python API](https://developers.google.com/gmail/api/quickstart/python) pacakge. The build job as an email should contain the python file to be run, and necessary data file as attachments. User can also configure the email whitelist to allow certain person to utilize your build server. The build result, including stdout, stderr, total running time, and any generated file will be replied to the sender when the job finishes. The end user only need to send an email, grab a cup of coffee, and wait for the email response.

Future works
* Performance: run multiple jobs in parallel
* System security: user should not be able to infringe system security
* More user interaction: user should be able to monitor their jobs and cancel jobs at any time

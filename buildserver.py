from gmailclient import GmailClient
import os
import subprocess
import random
import time

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
LOG = []
with open('conf/my_email', 'r') as f:
    MY_EMAIL = f.readline().strip()
FROM_EMAIL = MY_EMAIL

def run_command(cmd):
    cmd = cmd.strip().split()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out, err

def get_cmd_output(cmd):
    out, err = run_command(cmd)
    return out.strip()

def log(msg):
    msg = str(msg)
    print msg
    LOG.append(msg.strip())

def main():
    client = GmailClient()

    # check inbox for unread messages
    query = 'is:unread AND in:inbox AND from:%s AND has:attachment AND filename:py' % FROM_EMAIL
    messages = client.ListMessagesMatchingQuery('me', query)
    msg_labels = GmailClient.CreateMsgLabels(remove_labels=['UNREAD'])

    for msg in messages:
        message = client.GetMessage('me', msg['id'])

        # download attachments
        test_id = "%09d" % random.randint(0, 100000000)
        store_dir = os.path.join(ROOT_DIR, test_id)
        if not os.path.exists(store_dir):
            os.makedirs(store_dir)

        client.GetAttachments('me', msg['id'], store_dir)

        # attach source code
        os.chdir(store_dir)
        pycode = get_cmd_output('find %s -name *.py' % store_dir)
        log("#################### SRC CODE ##################")
        log(get_cmd_output('cat %s' % pycode))

        # run python code
        start_time = time.time()
        out, err = run_command('python %s' % pycode)
        total_time = time.time() - start_time
        log("#################### OUTPUT ####################")
        log(out)
        log("#################### ERROR #####################")
        log(err)
        log("#################### TOTAL TIME ################")
        log("Total time: %.3f seconds" % total_time)
        log("################################################")

        # send email
        subject = "Result for running %s, Test ID: %s" % (pycode.split('/')[-1], test_id)
        content = '\n'.join(LOG)
        message = GmailClient.CreateMessage(MY_EMAIL, FROM_EMAIL, subject, content)
        client.SendMessage('me', message)

        # mark as read
        client.ModifyMessage('me', msg['id'], msg_labels)


if __name__ == '__main__':
    main()
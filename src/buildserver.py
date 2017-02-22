from gmailclient import GmailClient
import os
import subprocess
import random
import time
import re

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
LOG = []
DEFAULT_PYCODE = 'main.py'
with open(os.path.join(ROOT_DIR, 'conf/my_email'), 'r') as f:
    MY_EMAIL = f.readline().strip()
with open(os.path.join(ROOT_DIR, 'conf/whitelist_emails'), 'r') as f:
    lines = f.readlines()
    lines = [l.strip() for l in lines if l.strip()]
    WHITELIST_EMAILS = set(lines)


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


def get_from_emails_query(emails):
    query = '{'
    for email in emails:
        query += 'from:%s ' % email
    query += '}'
    return query


def build(store_dir, test_id):
    # attach source code
    os.chdir(store_dir)
    code_files = get_cmd_output('find %s -name *.py' % store_dir).split('\n')
    pycode = None
    if len(code_files) == 1:
        pycode = code_files[0]
    elif len(code_files) > 1:
        if os.path.join(store_dir, DEFAULT_PYCODE) in code_files:
            pycode = os.path.join(store_dir, DEFAULT_PYCODE)
        else:
            log("Error: Multiple python files found. Please set one as main.py.")

    if pycode:
        log("#################### TEST ID ###################")
        log("Test ID: %s" % test_id)
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


def main():
    client = GmailClient()

    # check inbox for unread messages
    q_from_email = get_from_emails_query(WHITELIST_EMAILS)
    query = 'is:unread AND in:inbox AND %s AND has:attachment AND filename:py' % q_from_email
    messages = client.ListMessagesMatchingQuery('me', query)

    # mark messages as read
    msg_labels = GmailClient.CreateMsgLabels(remove_labels=['UNREAD'])
    for msg in messages:
        client.ModifyMessage('me', msg['id'], msg_labels)

    # process messages
    for msg in messages:
        message = client.GetMessage('me', msg['id'])

        # download attachments
        test_id = "%09d" % random.randint(0, 100000000)
        store_dir = os.path.join(ROOT_DIR, 'target', test_id)
        if not os.path.exists(store_dir):
            os.makedirs(store_dir)

        client.GetAttachments('me', msg['id'], store_dir)
        attachments = set(os.listdir(store_dir))

        # run build job
        build(store_dir, test_id)

        # check generated files
        generated_files = set(os.listdir(store_dir)) - attachments
        generated_files = [os.path.join(store_dir, f) for f in generated_files]

        # send result email
        content = '\n'.join(LOG) + '\n'
        message = GmailClient.CreateReplyMessageWithAttachment(message, MY_EMAIL, content,
                                                               generated_files)

        client.SendMessage('me', message)


if __name__ == '__main__':
    main()
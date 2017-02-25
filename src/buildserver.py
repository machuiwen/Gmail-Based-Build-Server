from gmailclient import GmailClient
import os
import subprocess
import random
import time
import re
from multiprocessing import Pool

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
DEFAULT_PYCODE_FILENAME = 'main.py'
MY_EMAIL_FILE = 'conf/my_email'
WHITELIST_EMAILS_FILE = 'conf/whitelist_emails'
TARGET_DIR = 'target'


class BuildServer(object):
    def __init__(self):
        with open(os.path.join(ROOT_DIR, MY_EMAIL_FILE), 'r') as f:
            self.my_email = f.readline().strip()
        with open(os.path.join(ROOT_DIR, WHITELIST_EMAILS_FILE), 'r') as f:
            lines = f.readlines()
            lines = [l.strip() for l in lines if l.strip()]
            self.whitelist_emails = set(lines)
        self.LOG = {}
        self.client = GmailClient()
        self.user_id = 'me'
        self.n_processes = 4


    @staticmethod
    def run_command(cmd):
        cmd = cmd.strip().split()
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return out, err


    @staticmethod
    def get_cmd_output(cmd):
        out, err = BuildServer.run_command(cmd)
        return out.strip()


    def log(self, test_id, msg):
        msg = str(msg)
        print msg
        if test_id not in self.LOG:
            self.LOG[test_id] = []
        self.LOG[test_id].append(msg.strip())


    def get_whitelist_emails_query(self):
        query = '{'
        for email in self.whitelist_emails:
            query += 'from:%s ' % email
        query += '}'
        return query


    def build(self, store_dir, test_id):
        # attach source code
        os.chdir(store_dir)
        code_files = BuildServer.get_cmd_output('find %s -name *.py' % store_dir).split('\n')
        pycode = None
        if len(code_files) == 1:
            pycode = code_files[0]
        elif len(code_files) > 1:
            if os.path.join(store_dir, DEFAULT_PYCODE_FILENAME) in code_files:
                pycode = os.path.join(store_dir, DEFAULT_PYCODE_FILENAME)
            else:
                self.log(test_id, "Error: Multiple python files found. Please set one as main.py.")

        if pycode:
            self.log(test_id, "#################### TEST ID ###################")
            self.log(test_id, "Test ID: %s" % test_id)
            self.log(test_id, "#################### SRC CODE ##################")
            self.log(test_id, BuildServer.get_cmd_output('cat %s' % pycode))

            # run python code
            start_time = time.time()
            out, err = BuildServer.run_command('python %s' % pycode)
            total_time = time.time() - start_time
            self.log(test_id, "#################### OUTPUT ####################")
            self.log(test_id, out)
            self.log(test_id, "#################### ERROR #####################")
            self.log(test_id, err)
            self.log(test_id, "#################### TOTAL TIME ################")
            self.log(test_id, "Total time: %.3f seconds" % total_time)
            self.log(test_id, "################################################")


    def main(self):
        # check inbox for unread messages
        query = 'is:unread AND in:inbox AND %s AND has:attachment AND filename:py' % \
                self.get_whitelist_emails_query()
        messages = self.client.ListMessagesMatchingQuery(self.user_id, query)

        # mark messages as read
        msg_labels = GmailClient.CreateMsgLabels(remove_labels=['UNREAD'])
        for msg in messages:
            self.client.ModifyMessage(self.user_id, msg['id'], msg_labels)


        # process messages
        for msg in messages:
            message = self.client.GetMessage(self.user_id, msg['id'])

            # download attachments
            test_id = "%09d" % random.randint(0, 100000000)
            store_dir = os.path.join(ROOT_DIR, TARGET_DIR, test_id)
            if not os.path.exists(store_dir):
                os.makedirs(store_dir)

            self.client.GetAttachments(self.user_id, msg['id'], store_dir)
            attachments = set(os.listdir(store_dir))

            # run build job
            self.build(store_dir, test_id)

            # check generated files
            generated_files = set(os.listdir(store_dir)) - attachments
            generated_files = [os.path.join(store_dir, f) for f in generated_files]

            # send result email
            content = '\n'.join(self.LOG[test_id]) + '\n'
            message = GmailClient.CreateReplyMessageWithAttachment(message, self.my_email, content,
                                                                   generated_files)
            self.client.SendMessage(self.user_id, message)


if __name__ == '__main__':
    server = BuildServer()
    server.main()

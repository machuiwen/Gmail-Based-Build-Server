from __future__ import print_function
import base64
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mimetypes
import os
from apiclient import errors
from apiservice import GmailService
import re


class GmailClient(object):
    def __init__(self):
        # Authorize Gmail API service instance
        self.service = GmailService().get_service()


    @staticmethod
    def _get_message_header(message, key):
        for h in message['payload']['headers']:
            if h['name'].lower() == key.lower():
                return h['value']
        raise ValueError("Message %s doesn't have header '%s'." % (message['id'], key))


    @staticmethod
    def _add_message_attachments(message, attached_files):
        for path in attached_files:
            filename = path.split('/')[-1]
            content_type, encoding = mimetypes.guess_type(path)

            if content_type is None or encoding is not None:
                content_type = 'application/octet-stream'

            main_type, sub_type = content_type.split('/', 1)

            if main_type == 'text':
                with open(path, 'rb') as fp:
                    msg = MIMEText(fp.read(), _subtype=sub_type)
            elif main_type == 'image':
                with open(path, 'rb') as fp:
                    msg = MIMEImage(fp.read(), _subtype=sub_type)
            elif main_type == 'audio':
                with open(path, 'rb') as fp:
                    msg = MIMEAudio(fp.read(), _subtype=sub_type)
            else:
                with open(path, 'rb') as fp:
                    msg = MIMEBase(main_type, sub_type)
                    msg.set_payload(fp.read())

            msg.add_header('Content-Disposition', 'attachment', filename=filename)
            message.attach(msg)
        return message


    def SendMessage(self, user_id, message):
        """Send an email message.

        Args:
            user_id: User's email address. The special value "me"
            can be used to indicate the authenticated user.
            message: Message to be sent.

        Returns:
            Sent Message.
        """
        try:
            message = (self.service.users().messages().send(userId=user_id, body=message)
                .execute())
            print('Sent Message Id: %s' % message['id'])
            return message
        except errors.HttpError, error:
            print('An error occurred: %s' % error)


    @staticmethod
    def CreateMessage(sender, to, subject, message_text):
        """Create a message for an email.

        Args:
            sender: Email address of the sender.
            to: Email address of the receiver.
            subject: The subject of the email message.
            message_text: The text of the email message.

        Returns:
            An object containing a base64url encoded email object.
        """
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        return {'raw': base64.urlsafe_b64encode(message.as_string())}


    @staticmethod
    def CreateMessageWithAttachment(sender, to, subject, message_text, attached_files=[]):
        """Create a message for an email.

        Args:
            sender: Email address of the sender.
            to: Email address of the receiver.
            subject: The subject of the email message.
            message_text: The text of the email message.
            attached_files: The full path of the attached files. Type: List.

        Returns:
            An object containing a base64url encoded email object.
        """
        message = MIMEMultipart()
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject

        msg = MIMEText(message_text)
        message.attach(msg)
        message = GmailClient._add_message_attachments(message, attached_files)

        return {'raw': base64.urlsafe_b64encode(message.as_string())}


    @staticmethod
    def CreateReplyMessageWithAttachment(in_message, replyer, reply_text, attached_files=[]):
        """Create a reply message for an email.

        Args:
            in_message: The message to be replied to.
            reply_text: The text of the reply message.
            attached_files: The full path of the attached files. Type: List.

        Returns:
            An object containing a base64url encoded email object.
        """

        message = MIMEMultipart()
        message['from'] = replyer
        sender = re.findall('<([^>]*)>', GmailClient._get_message_header(in_message, 'From'))[0]
        message['to'] = sender
        subject = GmailClient._get_message_header(in_message, 'Subject')
        if subject.lower().startswith('re: '):
            message['subject'] = 'Re: ' + subject[4:]
        else:
            message['subject'] = 'Re: ' + subject
        message_internal_id = GmailClient._get_message_header(in_message, 'Message-Id')
        message['In-Reply-To'] = message_internal_id
        try:
            references = GmailClient._get_message_header(in_message, 'References')
        except ValueError:
            message['References'] = message_internal_id
        else:
            message['References'] = references + ' ' + message_internal_id

        msg = MIMEText(reply_text)
        message.attach(msg)
        message = GmailClient._add_message_attachments(message, attached_files)

        return {'raw': base64.urlsafe_b64encode(message.as_string()),
                'threadId': in_message['threadId']}


    def GetMessage(self, user_id, msg_id):
        """Get a Message with given ID.

        Args:
            user_id: User's email address. The special value "me"
            can be used to indicate the authenticated user.
            msg_id: The ID of the Message required.

        Returns:
            A Message.
        """
        try:
            message = self.service.users().messages().get(userId=user_id, id=msg_id).execute()
            return message
        except errors.HttpError, error:
            print('An error occurred: %s' % error)


    def ListMessagesMatchingQuery(self, user_id, query=''):
        """List all Messages of the user's mailbox matching the query.

        Args:
            user_id: User's email address. The special value "me"
            can be used to indicate the authenticated user.
            query: String used to filter messages returned.
            Eg.- 'from:user@some_domain.com' for Messages from a particular sender.

        Returns:
            List of Messages that match the criteria of the query. Note that the
            returned list contains Message IDs, you must use get with the
            appropriate ID to get the details of a Message.
        """
        try:
            response = self.service.users().messages().list(userId=user_id, q=query).execute()
            messages = []
            if 'messages' in response:
                messages.extend(response['messages'])

            while 'nextPageToken' in response:
                page_token = response['nextPageToken']
                response = self.service.users().messages().list(userId=user_id, q=query, pageToken=page_token).execute()
                messages.extend(response['messages'])

            return messages
        except errors.HttpError, error:
            print('An error occurred: %s' % error)


    def GetAttachments(self, user_id, msg_id, store_dir):
        """Get and store attachment from Message with given id.

        Args:
            user_id: User's email address. The special value "me"
            can be used to indicate the authenticated user.
            msg_id: ID of Message containing attachment.
            store_dir: The directory used to store attachments.
        """
        try:
            message = self.service.users().messages().get(userId=user_id, id=msg_id).execute()

            for part in message['payload']['parts']:
                if part['filename']:
                    attachment_id = part['body']['attachmentId']
                    attachment = self.service.users().messages().attachments().get(
                        userId=user_id, messageId=msg_id, id=attachment_id).execute()

                    file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
                    path = os.path.join(store_dir, part['filename'])

                    with open(path, 'w') as f:
                        f.write(file_data)

            print('Attachments stored in: %s' % store_dir)

        except errors.HttpError, error:
            print('An error occurred: %s' % error)


    def ModifyMessage(self, user_id, msg_id, msg_labels):
        """Add/remove labels to a given message.

        Args:
            user_id: User's email address. The special value "me"
            can be used to indicate the authenticated user.
            msg_id: The id of the message required.
            msg_labels: The change in labels.

        Returns:
            Modified message, containing updated labelIds, id and threadId.
        """
        try:
            message = self.service.users().messages().modify(userId=user_id, id=msg_id,
                body=msg_labels).execute()
            label_ids = message['labelIds']
            return message
        except errors.HttpError, error:
            print('An error occurred: %s' % error)


    @staticmethod
    def CreateMsgLabels(add_labels=[], remove_labels=[]):
        """Create object to update labels.

        Returns:
            A label update object.
        """
        label_update = {}
        label_update['removeLabelIds'] = remove_labels
        label_update['addLabelIds'] = add_labels
        return label_update


if __name__ == '__main__':
    pass

import os
import sys
import base64
import json
from base64 import urlsafe_b64decode
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import ai_evaluation
import upload_to_monday

def external_path(filename):
    """Return path to filename next to executable or script."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

CONFIG_FILE = external_path('config.json')

def load_or_prompt_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                print("Config file is corrupted. Recreating it.")
    
    if 'api_key' not in config:
        config["api_key"] = input("Enter your Monday.com API key: ").strip()
    if 'board_id' not in config:
        config['board_id'] = int(input("Enter your Monday.com board ID: "))
    if 'group_id' not in config:
        config['group_id'] = input("Enter your Monday.com group ID: ")
    if 'openai_api_key' not in config:
        config['openai_api_key'] = input("Enter your openAI API key: ")

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

    return config

config = load_or_prompt_config()
default_api_key = config['api_key']
default_board_id = config['board_id']
default_group_id = config['group_id']
openai_api_key = config['openai_api_key']

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def _decode_base64(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('UTF-8', errors='replace')

def authenticate_gmail():
    TOKEN_FILE = external_path('token.json')
    CREDENTIALS_FILE = external_path('credentials.json')

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_n_emails(service, n):
    def _parse_payload(parts):
        plain, html, attachments = None, None, []
        for part in parts:
            mime = part.get('mimeType', '')
            body = part.get('body', {})

            if part.get('parts'):
                p, h, a = _parse_payload(part['parts'])
                if p and not plain:
                    plain = p
                if h and not html:
                    html = h
                attachments.extend(a)
            elif mime == 'text/plain' and body.get('data'):
                plain = _decode_base64(body['data'])
            elif mime == 'text/html' and body.get('data'):
                html = _decode_base64(body['data'])
            else:
                filename = part.get('filename')
                att_id = body.get('attachmentId')
                if filename and att_id:
                    attachments.append({
                        'filename': filename,
                        'attachmentId': att_id,
                        'mimeType': mime
                    })
        return plain, html, attachments

    results = service.users().messages().list(
        userId='me', maxResults=n, labelIds=['INBOX']
    ).execute()
    messages = results.get('messages', [])

    email_list = []

    for message in messages:
        msg = service.users().messages().get(
            userId='me', id=message['id'], format='full'
        ).execute()
        payload = msg.get('payload', {})
        headers = payload.get('headers', [])

        email_info = {
            'id': message['id'],
            'subject': None,
            'from': None,
            'body': None,
            'attachments': []
        }

        for header in headers:
            if header['name'] == 'Subject':
                email_info['subject'] = header['value']
            elif header['name'] == 'From':
                email_info['from'] = header['value']

        if payload.get('parts'):
            plain_text, html_text, attachments = _parse_payload(payload['parts'])
        else:
            mime = payload.get('mimeType', '')
            body = payload.get('body', {})
            data = body.get('data')
            plain_text = None
            html_text = None
            if data:
                if mime == 'text/plain':
                    plain_text = _decode_base64(data)
                elif mime == 'text/html':
                    html_text = _decode_base64(data)
            filename = payload.get('filename')
            att_id = body.get('attachmentId')
            attachments = []
            if filename and att_id:
                attachments.append({
                    'filename': filename,
                    'attachmentId': att_id,
                    'mimeType': mime
                })

        email_info['body'] = plain_text or html_text
        email_info['attachments'] = attachments
        email_list.append(email_info)
    return email_list


def download_attachments(service, email_list, base_folder='attachments'):
    os.makedirs(base_folder, exist_ok=True)
    for email in email_list:
        message_id = email.get('id')
        if not message_id or not email.get('attachments'):
            continue
        raw_subj = email.get('subject') or 'no_subject'
        safe_subj = "".join(
            c for c in raw_subj if c.isalnum() or c in " _-"
        ).strip() or 'no_subject'
        folder_path = os.path.join(base_folder, safe_subj)
        os.makedirs(folder_path, exist_ok=True)
        for att in email['attachments']:
            attach_id = att['attachmentId']
            filename = att['filename'] or attach_id
            attachment = service.users().messages().attachments().get(
                userId='me', messageId=message_id, id=attach_id
            ).execute()
            data = urlsafe_b64decode(attachment['data'].encode('UTF-8'))
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'wb') as f:
                f.write(data)


def main():
    service = authenticate_gmail()
    email_list = get_n_emails(service, input("Enter the amount of emails to check: "))

    for email in email_list:
        body = email.get('body', '')
        analysis = ai_evaluation.analyze_email(body, openai_api_key)
        if analysis.strip().lower().startswith('yes'):
            lines = analysis.splitlines()
            if lines and lines[0].strip().lower() == 'yes':
                update_text = "\n".join(lines[1:]).strip()
            else:
                update_text = analysis.strip()

            item_name = ai_evaluation.get_company_title(body, openai_api_key)

            download_attachments(service, [email])

            raw_subj = email.get('subject') or 'no_subject'
            safe_subj = "".join(
                c for c in raw_subj if c.isalnum() or c in " _-"
            ).strip() or 'no_subject'
            base_folder = 'attachments'
            attachment_paths = []
            for att in email['attachments']:
                filename = att['filename'] or att['attachmentId']
                path = os.path.join(base_folder, safe_subj, filename)
                if os.path.exists(path):
                    attachment_paths.append(path)

            upload_to_monday.create_item_with_update_and_files(
                api_key=default_api_key,
                board_id=default_board_id,
                group_id=default_group_id,
                item_name=item_name,
                update_text=update_text,
                file_paths=attachment_paths
            )

if __name__ == '__main__':
    main()
    input()

import os
import json
import logging
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

import config

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/calendar'
]

def get_google_services():
    """Authenticates and returns Drive, Docs, and Calendar service clients."""
    creds = None
    token_path = os.path.join(config.BASE_DIR, 'token.json')
    creds_path = os.path.join(config.BASE_DIR, config.GOOGLE_CREDENTIALS_PATH)
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(f"OAuth credentials not found at {creds_path}. Download from Google Cloud Console.")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=8080)
            
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)
        calendar_service = build('calendar', 'v3', credentials=creds)
        return drive_service, docs_service, calendar_service
    except Exception as e:
        logger.error(f"Failed to build Google services: {e}")
        return None, None, None

def _get_or_create_folder(drive_service, folder_name: str, parent_id: str = None) -> str:
    """Finds a Google Drive folder by name or creates it, returning its ID."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
        
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if not items:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
            
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    else:
        return items[0].get('id')

def save_to_drive(drive_service, title: str, content_bundle: dict) -> str:
    """Saves raw JSON bundle to an 'EpiCred Content/Raw' Drive folder. Returns file ID."""
    try:
        root_folder = _get_or_create_folder(drive_service, "EpiCred Content")
        json_folder = _get_or_create_folder(drive_service, "Raw JSON", root_folder)
        
        file_metadata = {
            'name': f"RAW_{datetime.now().strftime('%Y%m%d')}_{title}.json",
            'parents': [json_folder]
        }
        media = MediaIoBaseUpload(io.BytesIO(json.dumps(content_bundle, indent=2).encode('utf-8')),
                                  mimetype='application/json', resumable=True)
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
    except Exception as e:
        logger.error(f"Save to Drive failed: {e}")
        return None

def create_google_doc(drive_service, docs_service, title: str, content_bundle: dict) -> str:
    """Creates a formatted Google Doc with all content sections. Returns Doc ID."""
    try:
        root_folder = _get_or_create_folder(drive_service, "EpiCred Content")
        docs_folder = _get_or_create_folder(drive_service, "Formatted Docs", root_folder)
        
        # 1. Create empty file in Drive folder
        file_metadata = {
            'name': f"Content: {title}",
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [docs_folder]
        }
        doc_file = drive_service.files().create(body=file_metadata, fields='id').execute()
        doc_id = doc_file.get('id')
        
        # 2. Compile document text
        text_content = f"Campaign: {title}\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        for platform, data in content_bundle.items():
            if not data:
                continue
            text_content += f"\n{'='*40}\n[{platform.replace('_', ' ').upper()}]\n{'='*40}\n"
            text_content += json.dumps(data, indent=2) + "\n"
        
        requests = [{'insertText': {'location': {'index': 1}, 'text': text_content}}]

        # 3. Batch Update Doc
        if text_content:
            docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
            
        logger.info(f"Created Google Doc ID: {doc_id}")
        return doc_id
    except Exception as e:
        logger.error(f"Create Google Doc failed: {e}")
        return None

def schedule_calendar_event(calendar_service, title: str, doc_id: str, platform: str):
    """Creates a Calendar Event containing the link to the generated Google Doc."""
    try:
        PLATFORM_RULES = config.PLATFORM_RULES
        rule = PLATFORM_RULES.get(platform)
        if not rule:
            return None
            
        # Very simple scheduling logic: just slot it on the first available matching day in the next 7 days
        today = datetime.now()
        target_day = None
        for i in range(1, 8):
            dt = today + timedelta(days=i)
            if dt.weekday() in rule['days']:
                time_parts = rule['time'].split(':')
                target_day = dt.replace(hour=int(time_parts[0]), minute=int(time_parts[1]), second=0)
                break
                
        if not target_day:
            target_day = today + timedelta(days=1, hours=2)

        start_time = target_day.isoformat()
        end_time = (target_day + timedelta(minutes=30)).isoformat()
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        
        event = {
          'summary': f"Post: {platform.replace('_', ' ').title()}",
          'description': f"Content Campaign: {title}\nReview Document: {doc_url}",
          'start': {'dateTime': start_time, 'timeZone': 'Asia/Kolkata'},
          'end': {'dateTime': end_time, 'timeZone': 'Asia/Kolkata'},
          'colorId': rule.get('color', '1')
        }
        
        created_event = calendar_service.events().insert(calendarId='primary', body=event).execute()
        return created_event.get('htmlLink')
    except Exception as e:
        logger.error(f"Calendar schedule failed for {platform}: {e}")
        return None

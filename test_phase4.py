import sys
import os
import json
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline.google_integration import get_google_services, save_to_drive, create_google_doc, schedule_calendar_event

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

print("\n" + "="*60)
print("  EpiCred Phase 4 — Google Workspace Integration Test")
print("="*60)

if not os.path.exists("test_phase3_output.json"):
    logger.error("test_phase3_output.json not found! Run Phase 3 first.")
    sys.exit(1)

with open("test_phase3_output.json", "r", encoding="utf-8") as f:
    content_bundle = json.load(f)

# Title for the dummy campaign
campaign_title = "Study Abroad Fair May 2026"

print("\n[ Authenticating via OAuth ]")
drive_service, docs_service, calendar_service = get_google_services()

if not drive_service:
    logger.error("\n❌ Authentication failed or was cancelled.")
    sys.exit(1)

print("\n[ 1. Saving Raw JSON to Google Drive ]")
file_id = save_to_drive(drive_service, campaign_title, content_bundle)
print(f" -> Drive File ID: {file_id}")

print("\n[ 2. Creating Formatted Google Doc ]")
doc_id = create_google_doc(drive_service, docs_service, campaign_title, content_bundle)
print(f" -> Google Doc ID: {doc_id}")
if doc_id:
    print(f" -> Link: https://docs.google.com/document/d/{doc_id}/edit")

print("\n[ 3. Scheduling Content on Google Calendar ]")
if calendar_service and doc_id:
    for platform, data in content_bundle.items():
        if data:  # If we actually generated content for this platform
            print(f" -> Scheduling {platform}...")
            event_link = schedule_calendar_event(calendar_service, campaign_title, doc_id, platform)
            if event_link:
                print(f"    ✅ Scheduled! Event Link: {event_link}")

print("\n" + "="*60)
print("  ✅ PHASE 4 INTEGRATION COMPLETE")
print("="*60)

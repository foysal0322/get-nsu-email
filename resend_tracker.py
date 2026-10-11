import os
import json
import time
from typing import List, Dict, Any, Optional
import resend

def load_env(env_path: str = '.env'):
    """Load environment variables from a .env file."""
    if not os.path.exists(env_path):
        return
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

# Automatically load .env from current directory or script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
load_env(os.path.join(script_dir, '.env'))

RESEND_API_KEY = os.getenv('RESEND_API_KEY')
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'onboarding@resend.dev')

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

def send_tracked_email(
    to: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Sends an email using Resend with automatic open and click tracking.
    
    :param to: Recipient email address
    :param subject: Email subject line
    :param html_content: HTML content of the email
    :param from_email: Sender email (defaults to SENDER_EMAIL)
    :param tags: Optional metadata tags
    :return: Response dict containing email id
    """
    if not RESEND_API_KEY or RESEND_API_KEY == 'your_resend_api_key_here':
        raise ValueError("Please configure a valid RESEND_API_KEY in your .env file!")
    
    params: resend.Emails.SendParams = {
        "from": from_email or SENDER_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html_content,
    }
    
    if tags:
        params["tags"] = tags
        
    return resend.Emails.send(params)

def check_email_status(email_id: str) -> Dict[str, Any]:
    """
    Fetches the delivery, open, and click status of an email by its ID.
    """
    if not RESEND_API_KEY or RESEND_API_KEY == 'your_resend_api_key_here':
        raise ValueError("Please configure a valid RESEND_API_KEY in your .env file!")
    return resend.Emails.get(email_id)

def send_to_matched_recipients(
    json_path: str = 'matched_commentators.json',
    subject: str = 'Regarding your inquiry',
    template_html: str = '<p>Hello {{name}},</p><p>This is a tracked message.</p>',
    delay_between_sends: float = 0.5,
    max_send: Optional[int] = None
):
    """
    Batch sends tracked emails to matched commentators from JSON.
    """
    if not os.path.isabs(json_path):
        json_path = os.path.join(script_dir, json_path)

    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        recipients = json.load(f)
        
    valid_recipients = [
        r for r in recipients 
        if r.get('email') and r['email'] != 'N/A' and '@' in r['email']
    ]
    
    print(f"Found {len(valid_recipients)} valid recipients with emails.")
    if max_send:
        valid_recipients = valid_recipients[:max_send]
        print(f"Limiting to first {max_send} recipients.")
        
    log_results = []
    
    for idx, recipient in enumerate(valid_recipients, 1):
        name = recipient.get('name', 'Student')
        email = recipient.get('email')
        
        personalized_html = template_html.replace('{{name}}', name)
        
        try:
            print(f"[{idx}/{len(valid_recipients)}] Sending to {name} ({email})...")
            res = send_tracked_email(
                to=email,
                subject=subject,
                html_content=personalized_html,
                tags=[
                    {"name": "recipient_name", "value": name[:40]},
                    {"name": "condition", "value": recipient.get("matched_condition", "matched")[:40]}
                ]
            )
            email_id = res.get("id")
            print(f"  [OK] Sent! Resend ID: {email_id}")
            log_results.append({
                "name": name,
                "email": email,
                "status": "sent",
                "resend_id": email_id,
                "sent_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            })
        except Exception as e:
            print(f"  [ERR] Error sending to {email}: {e}")
            log_results.append({
                "name": name,
                "email": email,
                "status": "failed",
                "error": str(e),
                "sent_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            })
            
        time.sleep(delay_between_sends)
        
    output_log = os.path.join(script_dir, 'sent_emails_log.json')
    with open(output_log, 'w', encoding='utf-8') as f:
        json.dump(log_results, f, indent=2)
    print(f"\nCompleted! Delivery logs saved to {output_log}")

if __name__ == '__main__':
    print("Resend Email Tracker Utility")
    print("============================")
    if not RESEND_API_KEY or RESEND_API_KEY == 'your_resend_api_key_here':
        print("RESEND_API_KEY is not set in .env!")
        print("1. Sign up at https://resend.com (Free: 3,000 emails/mo)")
        print("2. Paste your API key into: C:\\Users\\SMFoysalAhmed\\Desktop\\get-nsu-email\\.env")
        print("3. Then run: python resend_tracker.py")
    else:
        print("[OK] API Key detected!")
        print("Ready to send tracked emails.")

---
name: instantly-email
description: Instantly email operations for OpenClaw. List, read, send test emails, reply, forward, patch, delete, count unread, and mark threads as read using the Instantly Email API endpoints.
version: 1.1.0
author: openclaw
---

# Instantly Email Skill

Manage Instantly inbox workflows through a local Python helper script:
- `instantly_email.py`

## Setup

1. Set API key:
   ```bash
   export INSTANTLY_API_KEY=your-api-key-here
   ```
2. Optional: override API base URL:
   ```bash
   export INSTANTLY_API_BASE_URL=https://api.instantly.ai
   ```
3. Use Python 3 to run commands from this skill folder.

## Required Endpoint Coverage

This skill supports these endpoints:

- `POST /api/v2/emails/test` - Send a test email
- `POST /api/v2/emails/reply` - Reply to an email
- `POST /api/v2/emails/forward` - Forward an email
- `GET /api/v2/emails` - List email
- `GET /api/v2/emails/{id}` - Get email
- `PATCH /api/v2/emails/{id}` - Patch email
- `DELETE /api/v2/emails/{id}` - Delete email
- `GET /api/v2/emails/unread/count` - Count unread emails
- `POST /api/v2/emails/threads/{thread_id}/mark-as-read` - Mark all emails in a thread as read

## Usage

All commands use `instantly_email.py`.

### List emails

```bash
python3 instantly_email.py list --limit 25
python3 instantly_email.py list --search "thread:THREAD_UUID"
python3 instantly_email.py list --is-unread --mode emode_focused
```

### Get email by id

```bash
python3 instantly_email.py get --email-id "EMAIL_UUID"
```

### Send test email

```bash
python3 instantly_email.py test --json '{"to":"person@example.com","subject":"Test","body":{"text":"Hello"}}'
```

### Reply to email

```bash
python3 instantly_email.py reply --json '{"reply_to_uuid":"EMAIL_UUID","eaccount":"sender@domain.com","subject":"Re: Hello","body":{"text":"Thanks for the note"}}'
```

### Forward email

```bash
python3 instantly_email.py forward --json '{"reply_to_uuid":"EMAIL_UUID","to":"target@example.com","subject":"Fwd: Hello","body":{"text":"Sharing this"}}'
```

### Patch email

```bash
python3 instantly_email.py patch --email-id "EMAIL_UUID" --json '{"is_read":true}'
```

### Delete email

```bash
python3 instantly_email.py delete --email-id "EMAIL_UUID"
```

### Count unread emails

```bash
python3 instantly_email.py unread-count
```

### Mark thread as read

```bash
python3 instantly_email.py mark-thread-read --thread-id "THREAD_UUID"
```

## Safety Rules

- Confirm before sending: test, reply, forward.
- Confirm before destructive change: patch, delete.
- Never fabricate missing fields; ask for missing payload keys.
- Preserve pagination cursors when listing large email sets.

## Example Prompts

- "List my latest Instantly emails."
- "Show email details for this email id."
- "Reply to this email with a short follow-up."
- "Forward this email to another recipient."
- "Mark this thread as read."
- "How many unread emails do I have in Instantly?"
- "Patch this email status."
- "Delete this email."
- "Send a test email from this account."
---
name: gog
description: Google Workspace CLI for Gmail, Calendar, Drive, Contacts, Sheets, and Docs.
homepage: https://gogcli.sh
metadata: {"clawdbot":{"emoji":"🎮","requires":{"bins":["gog"]},"install":[{"id":"brew","kind":"brew","formula":"steipete/tap/gogcli","bins":["gog"],"label":"Install gog (brew)"}]}}
---

# gog

Use `gog` for Gmail/Calendar/Drive/Contacts/Sheets/Docs. Requires OAuth setup.

Setup (once)
- `gog auth credentials /path/to/client_secret.json`
- `gog auth add you@gmail.com --services gmail,calendar,drive,contacts,sheets,docs`
- `gog auth list`

Common commands
- Calendar: `gog calendar events <calendarId> --from <iso> --to <iso>`
- Drive search: `gog drive search "query" --max 10`
- Contacts: `gog contacts list --max 20`
- Sheets get: `gog sheets get <sheetId> "Tab!A1:D10" --json`
- Sheets update: `gog sheets update <sheetId> "Tab!A1:B2" --values-json '[["A","B"],["1","2"]]' --input USER_ENTERED`
- Sheets append: `gog sheets append <sheetId> "Tab!A:C" --values-json '[["x","y","z"]]' --insert INSERT_ROWS`
- Sheets clear: `gog sheets clear <sheetId> "Tab!A2:Z"`
- Sheets metadata: `gog sheets metadata <sheetId> --json`
- Docs export: `gog docs export <docId> --format txt --out /tmp/doc.txt`
- Docs cat: `gog docs cat <docId>`

Gmail commands

Search and read:
- `gog gmail search 'newer_than:7d' --max 10`
- `gog gmail thread get <threadId>`
- `gog gmail thread get <threadId> --download`
- `gog gmail thread get <threadId> --download --out-dir ./attachments`
- `gog gmail get <messageId>`
- `gog gmail get <messageId> --format metadata`
- `gog gmail attachment <messageId> <attachmentId>`
- `gog gmail attachment <messageId> <attachmentId> --out ./attachment.bin`
- `gog gmail url <threadId>`
- `gog gmail thread modify <threadId> --add STARRED --remove INBOX`

Send and compose:
- `gog gmail send --to a@b.com --subject "Hi" --body "Plain fallback"`
- `gog gmail send --to a@b.com --subject "Hi" --body-file ./message.txt`
- `gog gmail send --to a@b.com --subject "Hi" --body-file -`
- `gog gmail send --to a@b.com --subject "Hi" --body "Plain fallback" --body-html "<p>Hello</p>"`
- `gog gmail forward <messageId> --to a@b.com --note "FYI"`
- `gog gmail forward <messageId> --to a@b.com --skip-attachments`
- `gog gmail send --reply-to-message-id <messageId> --quote --to a@b.com --subject "Re: Hi" --body "My reply"`
- `gog gmail drafts create --reply-to-message-id <messageId> --quote --subject "Re: Hi" --body "My reply"`
- `gog gmail drafts update <draftId> --reply-to-message-id <messageId> --quote --subject "Re: Hi" --body "My reply"`
- `gog gmail drafts update <draftId> --quote --subject "Re: Hi" --body "My reply"`
- `gog gmail drafts list`
- `gog gmail drafts create --subject "Draft" --body "Body"`
- `gog gmail drafts create --to a@b.com --subject "Draft" --body "Body"`
- `gog gmail drafts update <draftId> --subject "Draft" --body "Body"`
- `gog gmail drafts update <draftId> --to a@b.com --subject "Draft" --body "Body"`
- `gog gmail drafts send <draftId>`
- `gog gmail autoreply 'from:alerts@example.com newer_than:7d' --body-file ./reply.txt --label AutoReplied --dry-run`

Labels:
- `gog gmail labels list`
- `gog gmail labels get INBOX --json`
- `gog gmail labels create "My Label"`
- `gog gmail labels rename "Old Label" "New Label"`
- `gog gmail labels style "My Label" --text-color "#ffffff" --background-color "#4285f4"`
- `gog gmail labels modify <threadId> --add STARRED --remove INBOX`
- `gog gmail labels delete <labelIdOrName>`

Batch operations:
- `gog gmail batch delete <messageId> <messageId>`
- `gog gmail batch modify <messageId> <messageId> --add STARRED --remove INBOX`

Filters:
- `gog gmail filters list`
- `gog gmail filters create --from 'noreply@example.com' --add-label 'Notifications'`
- `gog gmail filters delete <filterId>`
- `gog gmail filters export --out ./filters.json`

Settings:
- `gog gmail autoforward get`
- `gog gmail autoforward enable --email forward@example.com`
- `gog gmail autoforward disable`
- `gog gmail forwarding list`
- `gog gmail forwarding add --email forward@example.com`
- `gog gmail sendas list`
- `gog gmail sendas create --email alias@example.com`
- `gog gmail vacation get`
- `gog gmail vacation enable --subject "Out of office" --message "..."`
- `gog gmail vacation disable`

Delegation (G Suite/Workspace):
- `gog gmail delegates list`
- `gog gmail delegates add --email delegate@example.com`
- `gog gmail delegates remove --email delegate@example.com`

Watch (Pub/Sub push):
- `gog gmail watch start --topic projects/<p>/topics/<t> --label INBOX`
- `gog gmail watch serve --bind 127.0.0.1 --token <shared> --hook-url http://127.0.0.1:18789/hooks/agent`
- `gog gmail watch serve --bind 0.0.0.0 --verify-oidc --oidc-email <svc@...> --hook-url <url>`
- `gog gmail watch serve --bind 127.0.0.1 --token <shared> --fetch-delay 5 --hook-url http://127.0.0.1:18789/hooks/agent`
- `gog gmail watch serve --bind 127.0.0.1 --token <shared> --exclude-labels SPAM,TRASH --hook-url http://127.0.0.1:18789/hooks/agent`
- `gog gmail history --since <historyId>`

Notes
- Set `GOG_ACCOUNT=you@gmail.com` to avoid repeating `--account`.
- For scripting, prefer `--json` plus `--no-input`.
- Sheets values can be passed via `--values-json` (recommended) or as inline rows.
- Docs supports export/cat/copy. In-place edits require a Docs API client (not in gog).
- Confirm before sending mail or creating events.

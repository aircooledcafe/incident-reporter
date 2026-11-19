#!/usr/bin/env python3
"""
Star Wars Themed SOC Investigation - Python Automation Script
Demonstrates:
  1. Connecting to customer domain (or local development)
  2. Customer setup & Investigation creation using human-readable IDs ('CUST-32700', 'INV000004')
  3. Escalation contacts, related escalated incidents, and external research creation
  4. Single-item evidence ingestion (Item 1)
  5. High-performance bulk evidence ingestion (Items 2-5)
"""

import os
import sys
import requests

# Base URL: Use your deployed domain or local dev
# In production on soc.example.com, target https://soc.example.com/api (no port 8000)
API_BASE = os.environ.get("API_BASE", "https://soc.example.com/api")
API_TOKEN = os.environ.get("API_TOKEN", "YOUR_API_TOKEN_HERE")

CUSTOMER_CODE = "CUST-32700"
INVESTIGATION_CODE = "INV000004"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json",
}

session = requests.Session()
session.headers.update(headers)

print(f"[*] Targeting API at: {API_BASE}")

# 1. Ensure Customer exists using human-readable customer_id
print(f"[*] Creating / verifying Customer '{CUSTOMER_CODE}'...")
customer_payload = {
    "name": "Corellian Engineering Corporation",
    "customer_id": "CUST-32700",
    "notes": "Enterprise client profile for Corellian Engineering Corporation.",
}
cust_res = session.post(f"{API_BASE}/customers/", json=customer_payload)
if cust_res.status_code == 201:
    print(f"[+] Customer created with code: {CUSTOMER_CODE}")
else:
    print(f"[+] Customer '{CUSTOMER_CODE}' already registered and ready for use.")

# 1b. Register Customer Escalation Contacts
contacts_payload = [
    {
        "customer": "CUST-32700",
        "name": "Mon Mothma",
        "escalation_tier": "PRIMARY",
        "notes": "Executive stakeholder & impacted mailbox owner; coordinating partner BEC notifications.",
    },
    {
        "customer": "CUST-32700",
        "name": "Wedge Antilles",
        "escalation_tier": "SECONDARY",
        "notes": "Restored after MFA reset; assisting with Conditional Access token-protection rollout.",
    },
]
for contact in contacts_payload:
    c_res = session.post(f"{API_BASE}/customer-contacts/", json=contact)
    if c_res.status_code == 201:
        print(f"[+] Added contact: {contact['name']} ({contact['escalation_tier']})")

# 2. Create Investigation referencing customer by CUSTOMER_CODE
print(f"[*] Creating Investigation '{INVESTIGATION_CODE}'...")
investigation_payload = {
    "customer": "CUST-32700",
    "investigation_id": "INV000004",
    "title": "Adversary-in-the-Middle (MitM) Phishing Leading to Mass Spam Wave & Multi-Account Takeover",
    "ticket_id": "SOC-2026-3277",
    "ticket_link": "https://soc.internal.example/tickets/SOC-2026-3277",
    "status": "INVESTIGATING",
    "lead_analyst": "Leia Organa",
    "summary": "Finance Director Lando Calrissian (l.calrissian@corellia-eng.example) clicked a spear-phishing link impersonating Kuat Drive Yards procurement and authenticated through an Evilginx-style Adversary-in-the-Middle (MitM) reverse proxy hosted at sso-corellia-auth.net (203.0.113.195). The proxy intercepted both credentials and post-MFA session cookies, enabling session replay from 198.51.100.42. The attacker enrolled a rogue TOTP MFA device, created hidden Exchange inbox rules moving bounce/reply warnings to RSS Subscriptions, and launched a 486-recipient internal and partner phishing spam wave. Three additional Corellian accounts (w.antilles, m.mothma, and h.solo) fell victim to the internal MitM wave before tenant-wide session revocation.",
    "action_plan": "1. Purge remaining 486 internal/partner phishing messages via Microsoft Purview / Exchange Search-Mailbox.\n2. Audit all mailboxes for hidden Inbox Rules (`MoveToFolder: RSS Subscriptions` / `DeleteMessage`) and rogue OAuth apps.\n3. Confirm with Kuat Drive Yards AP team that no wire transfers were initiated from spoofed invoice emails sent by `m.mothma`.\n4. Enforce token-binding / Continuous Access Evaluation (CAE) and phishing-resistant Passkeys/FIDO2 for Finance & Executive groups.",
    "key_customer_contacts": "Corellian Cloud Identity & Messaging Team: identity-ops@corellia-eng.example",
    "key_assets_affected": "M365-TENANT-CORELLIA (corellia-eng.example)\nEXO-MAILBOX-LCALRISSIAN\nEXO-MAILBOX-WANTILLES\nEXO-MAILBOX-MMOTHMA\nEXO-MAILBOX-HSOLO\nSPO-HYPERDRIVE-PROCUREMENT",
    "key_users_affected": "l.calrissian@corellia-eng.example\nw.antilles@corellia-eng.example\nm.mothma@corellia-eng.example\nh.solo@corellia-eng.example",
    "key_malicious_indicators": "203.0.113.195\n198.51.100.42\n192.0.2.84\nsso-corellia-auth.net\nkuat-invoice-portal.com\nhttps://sso-corellia-auth.net/common/oauth2/authorize",
}
inv_res = session.post(f"{API_BASE}/investigations/", json=investigation_payload)
if inv_res.status_code == 400 and "investigation_id" in inv_res.text:
    # If INVESTIGATION_CODE already exists, allow backend auto-generation of next INV######
    investigation_payload.pop("investigation_id", None)
    inv_res = session.post(f"{API_BASE}/investigations/", json=investigation_payload)
inv_res.raise_for_status()
inv_data = inv_res.json()
inv_id = inv_data.get("investigation_id") or INVESTIGATION_CODE
print(f"[+] Created Investigation '{inv_id}': '{inv_data['title']}'")

# 2b. Attach Related Escalated Incidents
related_incidents = [
    {
        "title": "IDP-2026-7710: Impossible Travel & Session Cookie Replay on l.calrissian",
        "link": "https://soc.internal.example/escalations/IDP-2026-7710",
        "analyst_name": "Cassian Andor",
    },
    {
        "title": "MAIL-2026-7724: Outbound Phishing Spam Burst (486 Messages) from Compromised Tenant Mailboxes",
        "link": "https://soc.internal.example/escalations/MAIL-2026-7724",
        "analyst_name": "Ahsoka Tano",
    },
]
for rel in related_incidents:
    rel_payload = {"investigation": inv_id, **rel}
    r_res = session.post(f"{API_BASE}/related-incidents/", json=rel_payload)
    r_res.raise_for_status()
    print(f"[+] Linked related incident: {rel['title']}")

# 2c. Attach External Research Links
external_research = [
    {
        "link": "https://attack.mitre.org/techniques/T1557/",
        "summary": "MITRE ATT&CK T1557 & T1539 - Adversary-in-the-Middle Reverse Proxy Phishing & Web Session Cookie Theft.",
        "analyst_name": "Leia Organa",
    },
    {
        "link": "https://attack.mitre.org/techniques/T1564/008/",
        "summary": "MITRE ATT&CK T1564.008 - Hide Artifacts: Email Hiding Rules in compromised cloud mailboxes.",
        "analyst_name": "Ahsoka Tano",
    },
]
for res_item in external_research:
    res_payload = {"investigation": inv_id, **res_item}
    er_res = session.post(f"{API_BASE}/external-research/", json=res_payload)
    er_res.raise_for_status()
    print(f"[+] Added research item: {res_item['link']}")

# 3. Ingest Individual Item (Item 1) referencing inv_id
print(f"\n[*] [Single Ingest] Ingesting Item 1 into '{inv_id}' via POST /api/evidence/...")
item_1 = {
    "evidence_type": "ATOMIC",
    "analyst_name": "Cassian Andor",
    "timestamp": "2026-10-26T11:04:12Z",
    "summary": "Spear-phishing email from billing@kuat-invoice-portal.com delivered link to AiTM reverse proxy https://sso-corellia-auth.net/common/oauth2/authorize.",
    "affected_asset": "EXO-MAILBOX-LCALRISSIAN",
    "affected_user": "l.calrissian@corellia-eng.example",
    "user_created_by_attacker": False,
    "malicious_hosts_ips": "203.0.113.195, kuat-invoice-portal.com, sso-corellia-auth.net, https://sso-corellia-auth.net/common/oauth2/authorize",
    "commands_run": "",
    "mitre_tactic": "Initial Access (TA0001); Credential Access (TA0006)",
    "mitre_technique": "T1566.002 - Phishing: Spearphishing Link; T1557 - Adversary-in-the-Middle",
    "related_log_link": "https://siem.internal.example/events/mdo-urlclick-66102",
    "is_key_evidence": True,
    "notes": "User clicked URL and completed Number Matching MFA through the Evilginx reverse proxy hosted at 203.0.113.195.",
}
item_1["investigation"] = inv_id
res_single = session.post(f"{API_BASE}/evidence/", json=item_1)
res_single.raise_for_status()
print(f"[+] [1/5] Created single item ID: {res_single.json()['id']} on {inv_id}")

# 4. Ingest Remaining 4 Items in Bulk (Items 2-5) referencing inv_id
print(f"\n[*] [Bulk Ingest] Ingesting remaining 4 items into '{inv_id}' via POST /api/evidence/bulk_create/...")
bulk_items = [
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Leia Organa",
        "timestamp": "2026-10-26T11:08:30Z",
        "summary": "Stolen ESTSAUTHPERSISTENT session cookie replayed from 198.51.100.42 to register a rogue Software OATH MFA token and create stealth Exchange inbox rule '_sav_sync'.",
        "affected_asset": "M365-TENANT-CORELLIA",
        "affected_user": "l.calrissian@corellia-eng.example",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "198.51.100.42",
        "commands_run": "New-InboxRule -Name '_sav_sync' -SubjectOrBodyContainsWords 'phish','hacked','fraud','undeliverable' -MoveToFolder 'RSS Subscriptions' -MarkAsRead $true",
        "mitre_tactic": "Credential Access (TA0006); Persistence (TA0003); Defense Evasion (TA0005)",
        "mitre_technique": "T1539 - Steal Web Session Cookie; T1098.005 - Account Manipulation: Device Registration; T1564.008 - Hide Artifacts: Email Hiding Rules",
        "related_log_link": "https://siem.internal.example/events/ual-new-inboxrule-66188",
        "is_key_evidence": True,
        "notes": "Inbox rule moved any incoming emails containing 'phish', 'hacked', 'fraud', or 'undeliverable' to RSS Subscriptions and marked them read.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Ahsoka Tano",
        "timestamp": "2026-10-26T11:16:00Z",
        "end_timestamp": "2026-10-26T11:29:45Z",
        "summary": "Automated Graph API script sent 486 internal and external phishing/spam messages from l.calrissian containing 'Q4 Tibanna & Hyperdrive Remittance Notice' link to sso-corellia-auth.net.",
        "affected_asset": "EXO-MAILBOX-LCALRISSIAN",
        "affected_user": "l.calrissian@corellia-eng.example",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "198.51.100.42, sso-corellia-auth.net",
        "commands_run": "POST https://graph.microsoft.com/v1.0/me/sendMail [486 messages dispatched]",
        "mitre_tactic": "Lateral Movement (TA0008); Initial Access (TA0001)",
        "mitre_technique": "T1534 - Internal Spearphishing; T1566.002 - Phishing: Spearphishing Link",
        "search_result_link": "https://siem.internal.example/app/discover#/view/exo-spam-burst-486",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(event.provider:Exchange%20AND%20sender:l.calrissian@corellia-eng.example)",
        "is_key_evidence": True,
        "notes": "142 internal employees and 344 external supply-chain contacts received the lure before outbound rate-limiting triggered.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Leia Organa",
        "timestamp": "2026-10-26T11:24:10Z",
        "end_timestamp": "2026-10-26T11:42:05Z",
        "summary": "Secondary multi-account takeover: w.antilles, m.mothma, and h.solo authenticated via internal spam link and had session tokens hijacked from 192.0.2.84.",
        "affected_asset": "M365-TENANT-CORELLIA",
        "affected_user": "w.antilles@corellia-eng.example, m.mothma@corellia-eng.example, h.solo@corellia-eng.example",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "203.0.113.195, 192.0.2.84, sso-corellia-auth.net",
        "commands_run": "",
        "mitre_tactic": "Credential Access (TA0006); Lateral Movement (TA0008); Persistence (TA0003)",
        "mitre_technique": "T1539 - Steal Web Session Cookie; T1078.004 - Valid Accounts: Cloud Accounts",
        "search_result_link": "https://siem.internal.example/app/discover#/view/corellia-multi-ato",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(source.ip:(203.0.113.195%20OR%20192.0.2.84)%20AND%20outcome:success)",
        "is_key_evidence": True,
        "notes": "Attacker registered stealth inbox rules on all three compromised accounts and began secondary BEC thread hijacking from m.mothma.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Cassian Andor",
        "timestamp": "2026-10-26T11:47:19Z",
        "summary": "FileDownloaded events in Unified Audit Log: 28 supplier wire-routing PDFs downloaded from SharePoint site SPO-HYPERDRIVE-PROCUREMENT via hijacked m.mothma session.",
        "affected_asset": "SPO-HYPERDRIVE-PROCUREMENT",
        "affected_user": "m.mothma@corellia-eng.example",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "192.0.2.84",
        "commands_run": "",
        "mitre_tactic": "Collection (TA0009); Exfiltration (TA0010)",
        "mitre_technique": "T1213.002 - Data from Information Repositories: SharePoint; T1567.002 - Exfiltration Over Web Service: Exfiltration to Cloud Storage",
        "related_log_link": "https://siem.internal.example/events/ual-spo-download-66410",
        "is_key_evidence": True,
        "notes": "SOC revoked refresh tokens across all 4 accounts at 11:51 UTC, deleted rogue MFA devices & inbox rules, and blocked sso-corellia-auth.net.",
    },
]

bulk_payload = {
    "investigation": inv_id,
    "items": bulk_items,
}

res_bulk = session.post(f"{API_BASE}/evidence/bulk_create/", json=bulk_payload)
res_bulk.raise_for_status()
bulk_data = res_bulk.json()
print(f"[+] Bulk ingest completed! Added {bulk_data['count']} items in 1 atomic transaction.")

# 5. Verify Investigation Timeline using human-readable inv_id
print(f"\n[*] Verifying investigation timeline for '{inv_id}'...")
inv_detail = session.get(f"{API_BASE}/investigations/{inv_id}/").json()
total_timeline = len(inv_detail["timeline_events"])
print(f"[+] Total timeline events in Investigation '{inv_id}': {total_timeline}")

if total_timeline == 5:
    print(f"\n✅ Verification SUCCESS: 1 item ingested individually + 4 items ingested in bulk = 5 total items on '{inv_id}'!")
else:
    print(f"\n⚠️ Unexpected event count: expected 5, found {total_timeline}")

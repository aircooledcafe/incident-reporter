"""
Enterprise MITRE ATT&CK Tactics and Techniques catalog used for pairing
multi-selected tactics and techniques in incident summaries and reports.
"""

MITRE_TACTICS_WITH_TECHNIQUES = [
    {
        "tactic": "Reconnaissance (TA0043)",
        "techniques": [
            "T1595.001 - Active Scanning: Scanning IP Blocks",
            "T1595.002 - Active Scanning: Vulnerability Scanning",
            "T1592 - Gather Victim Host Information",
            "T1589.001 - Gather Victim Identity Information: Credentials",
            "T1589.002 - Gather Victim Identity Information: Email Addresses",
            "T1598.003 - Phishing for Information: Spearphishing Link",
        ],
    },
    {
        "tactic": "Resource Development (TA0042)",
        "techniques": [
            "T1583.001 - Acquire Infrastructure: Domains",
            "T1583.003 - Acquire Infrastructure: Virtual Private Server",
            "T1585.002 - Establish Accounts: Email Accounts",
            "T1588.002 - Obtain Capabilities: Tool",
            "T1608.001 - Stage Capabilities: Upload Malware",
            "T1608.005 - Stage Capabilities: Link Target",
        ],
    },
    {
        "tactic": "Initial Access (TA0001)",
        "techniques": [
            "T1190 - Exploit Public-Facing Application",
            "T1189 - Drive-by Compromise",
            "T1566.001 - Phishing: Spearphishing Attachment",
            "T1566.002 - Phishing: Spearphishing Link",
            "T1566.003 - Phishing: Spearphishing via Service",
            "T1078 - Valid Accounts",
            "T1078.002 - Valid Accounts: Domain Accounts",
            "T1078.004 - Valid Accounts: Cloud Accounts",
            "T1110.003 - Brute Force: Password Spraying",
            "T1133 - External Remote Services",
        ],
    },
    {
        "tactic": "Execution (TA0002)",
        "techniques": [
            "T1059 - Command and Scripting Interpreter",
            "T1059.001 - Command and Scripting Interpreter: PowerShell",
            "T1059.003 - Command and Scripting Interpreter: Windows Command Shell",
            "T1059.004 - Command and Scripting Interpreter: Unix Shell",
            "T1059.007 - Command and Scripting Interpreter: JavaScript",
            "T1204.001 - User Execution: Malicious Link",
            "T1204.002 - User Execution: Malicious File",
            "T1204.004 - User Execution: Malicious Copy and Paste",
            "T1047 - Windows Management Instrumentation",
            "T1053.005 - Scheduled Task/Job: Scheduled Task",
        ],
    },
    {
        "tactic": "Persistence (TA0003)",
        "techniques": [
            "T1505.003 - Server Software Component: Web Shell",
            "T1136.001 - Create Account: Local Account",
            "T1136.002 - Create Account: Domain Account",
            "T1136.003 - Create Account: Cloud Account",
            "T1098 - Account Manipulation",
            "T1098.002 - Account Manipulation: Additional Email Delegate Permissions",
            "T1098.005 - Account Manipulation: Device Registration",
            "T1053.003 - Scheduled Task/Job: Cron",
            "T1053.005 - Scheduled Task/Job: Scheduled Task",
            "T1547.001 - Boot or Logon Autostart Execution: Registry Run Keys",
        ],
    },
    {
        "tactic": "Privilege Escalation (TA0004)",
        "techniques": [
            "T1068 - Exploitation for Privilege Escalation",
            "T1078.002 - Valid Accounts: Domain Accounts",
            "T1098 - Account Manipulation",
            "T1134.001 - Access Token Manipulation: Token Impersonation/Theft",
            "T1484.001 - Domain Policy Modification: Group Policy Modification",
            "T1548.002 - Abuse Elevation Control Mechanism: Bypass User Account Control",
        ],
    },
    {
        "tactic": "Defense Evasion (TA0005)",
        "techniques": [
            "T1218.005 - System Binary Proxy Execution: Mshta",
            "T1218.011 - System Binary Proxy Execution: Rundll32",
            "T1027 - Obfuscated Files or Information",
            "T1140 - Deobfuscate/Decode Files or Information",
            "T1562.001 - Impair Defenses: Disable or Modify Tools",
            "T1070.004 - Indicator Removal: File Deletion",
            "T1564.008 - Hide Artifacts: Email Hiding Rules",
            "T1550.001 - Use Alternate Authentication Material: Application Access Token",
            "T1550.004 - Use Alternate Authentication Material: Web Session Cookie",
        ],
    },
    {
        "tactic": "Credential Access (TA0006)",
        "techniques": [
            "T1557 - Adversary-in-the-Middle",
            "T1539 - Steal Web Session Cookie",
            "T1528 - Steal Application Access Token",
            "T1111 - Multi-Factor Authentication Interception",
            "T1621 - Multi-Factor Authentication Request Generation",
            "T1110.003 - Brute Force: Password Spraying",
            "T1003.001 - OS Credential Dumping: LSASS Memory",
            "T1003.003 - OS Credential Dumping: NTDS",
            "T1003.006 - OS Credential Dumping: DCSync",
            "T1558.003 - Steal or Forge Kerberos Tickets: Kerberoasting",
            "T1552.001 - Unsecured Credentials: Credentials In Files",
            "T1555.003 - Credentials from Password Stores: Credentials from Web Browsers",
        ],
    },
    {
        "tactic": "Discovery (TA0007)",
        "techniques": [
            "T1087.002 - Account Discovery: Domain Account",
            "T1087.003 - Account Discovery: Email Account",
            "T1069.002 - Permission Groups Discovery: Domain Groups",
            "T1018 - Remote System Discovery",
            "T1046 - Network Service Discovery",
            "T1033 - System Owner/User Discovery",
            "T1082 - System Information Discovery",
            "T1083 - File and Directory Discovery",
        ],
    },
    {
        "tactic": "Lateral Movement (TA0008)",
        "techniques": [
            "T1021.001 - Remote Services: Remote Desktop Protocol",
            "T1021.002 - Remote Services: SMB/Windows Admin Shares",
            "T1021.004 - Remote Services: SSH",
            "T1021.006 - Remote Services: Windows Remote Management",
            "T1550.002 - Use Alternate Authentication Material: Pass the Hash",
            "T1550.003 - Use Alternate Authentication Material: Pass the Ticket",
            "T1550.004 - Use Alternate Authentication Material: Web Session Cookie",
            "T1534 - Internal Spearphishing",
        ],
    },
    {
        "tactic": "Collection (TA0009)",
        "techniques": [
            "T1114.002 - Email Collection: Remote Email Collection",
            "T1114.003 - Email Collection: Email Forwarding Rule",
            "T1213.002 - Data from Information Repositories: SharePoint",
            "T1039 - Data from Network Shared Drive",
            "T1005 - Data from Local System",
            "T1560.001 - Archive Collected Data: Archive via Utility",
        ],
    },
    {
        "tactic": "Command and Control (TA0011)",
        "techniques": [
            "T1071.001 - Application Layer Protocol: Web Protocols",
            "T1071.004 - Application Layer Protocol: DNS",
            "T1105 - Ingress Tool Transfer",
            "T1572 - Protocol Tunneling",
            "T1219 - Remote Access Software",
        ],
    },
    {
        "tactic": "Exfiltration (TA0010)",
        "techniques": [
            "T1041 - Exfiltration Over C2 Channel",
            "T1048.003 - Exfiltration Over Alternative Protocol: Unencrypted Non-C2 Protocol",
            "T1567.002 - Exfiltration Over Web Service: Exfiltration to Cloud Storage",
        ],
    },
    {
        "tactic": "Impact (TA0040)",
        "techniques": [
            "T1486 - Data Encrypted for Impact",
            "T1491.002 - Defacement: External Defacement",
            "T1496 - Resource Hijacking",
            "T1531 - Account Access Removal",
            "T1498 - Network Denial of Service",
        ],
    },
]

TECHNIQUE_CODE_TO_TACTICS: dict[str, list[str]] = {}
for _entry in MITRE_TACTICS_WITH_TECHNIQUES:
    _tactic = _entry["tactic"]
    for _tech in _entry["techniques"]:
        _code = _tech.split(" - ")[0].strip().upper()
        TECHNIQUE_CODE_TO_TACTICS.setdefault(_code, []).append(_tactic)

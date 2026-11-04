import re


def defang_text(text: str) -> str:
    """
    Defangs affected or malicious assets, hostnames, domains, files, IPs, and URLs:
      - https:// -> hxxps[:]//
      - http://  -> hxxp[:]//
      - 192.168.1.1 -> 192.168[.]1.1
      - domain.com  -> domain[.]com
      - sub.domain.com -> sub.domain[.]com
      - payload.exe -> payload[.]exe
    """
    if not text:
        return ""

    result = text

    # 1. Defang URL schemes: http:// -> hxxp[:]//, https:// -> hxxps[:]//, ftp:// -> fxp[:]//
    result = re.sub(r'(?i)\bhttps://', 'hxxps[:]//', result)
    result = re.sub(r'(?i)\bhttp://', 'hxxp[:]//', result)
    result = re.sub(r'(?i)\bftp://', 'fxp[:]//', result)

    # 2. Defang IPv4 addresses: e.g. 192.168.1.1 -> 192.168[.]1.1
    def _defang_ipv4(match):
        octets = match.group(0).split('.')
        if len(octets) == 4:
            return f"{octets[0]}.{octets[1]}[.]{octets[2]}.{octets[3]}"
        return match.group(0)

    result = re.sub(
        r'\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b',
        _defang_ipv4,
        result,
    )

    # 3. Defang domains, FQDN hostnames, and filenames by bracketing the final dot before the TLD / extension
    def _defang_domain_or_file(match):
        prefix = match.group(1)
        ext = match.group(2)
        if prefix.replace('.', '').isdigit() and ext.isdigit():
            return match.group(0)
        return f"{prefix}[.]{ext}"

    result = re.sub(
        r'\b([a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)*)\.([a-zA-Z0-9]{2,10})\b',
        _defang_domain_or_file,
        result,
    )

    return result


def split_to_bullet_items(raw_text: str, defang: bool = True) -> list[str]:
    """
    Splits a newline-, comma-, or semicolon-separated text block into clean individual items.
    """
    if not raw_text:
        return []
    parts = re.split(r'[\r\n,;]+', raw_text)
    items = []
    for p in parts:
        cleaned = p.strip().lstrip('-*• ').strip()
        if cleaned:
            items.append(defang_text(cleaned) if defang else cleaned)
    return items

import csv
import io
import os
import shutil
import zipfile
from pathlib import Path
from django.conf import settings
from PIL import Image as PilImage

from odf.opendocument import OpenDocumentText
from odf.style import (
    Style,
    TextProperties,
    ParagraphProperties,
    GraphicProperties,
    TableCellProperties,
)
from odf.text import H, P, Span, A, List, ListItem
from odf.draw import Frame, Image as OdfImage
from odf.table import Table as OdfTable, TableColumn, TableRow, TableCell

from .defang import defang_text, split_to_bullet_items


def format_dt(dt) -> str:
    if not dt:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _format_timestamp_range(item) -> str:
    if item.evidence_type == "SEARCH" and item.end_timestamp:
        return f"{format_dt(item.timestamp)} - {format_dt(item.end_timestamp)}"
    return format_dt(item.timestamp)


def _format_analyst_notes(item) -> str:
    parts = []
    if item.summary and item.summary.strip():
        parts.append(item.summary.strip())
    if item.notes and item.notes.strip():
        parts.append(item.notes.strip())
    return " — ".join(parts) if parts else "None"


def _collect_key_indicators(item) -> list[str]:
    """
    Collects and defangs malicious hosts, IPs, domains, files, URLs, and commands for an evidence item.
    """
    indicators = []
    for ind in split_to_bullet_items(item.malicious_hosts_ips, defang=True):
        indicators.append(ind)
    if item.commands_run:
        for cmd in item.commands_run.splitlines():
            if cmd.strip():
                indicators.append(f"Command: {defang_text(cmd.strip())}")
    return indicators


def _collect_links(item) -> list[str]:
    """
    Collects analyst-provided links to logs and searches WITHOUT defanging.
    """
    links = []
    if item.related_log_link and item.related_log_link.strip():
        links.append(item.related_log_link.strip())
    if item.search_result_link and item.search_result_link.strip():
        links.append(item.search_result_link.strip())
    if item.search_query_link and item.search_query_link.strip():
        links.append(item.search_query_link.strip())
    return links


def collect_project_assets(project, items) -> list[str]:
    """
    Returns unique defanged affected assets from the project overview and evidence items.
    """
    raw = split_to_bullet_items(project.key_assets_affected, defang=True)
    for item in items:
        for asset in split_to_bullet_items(item.affected_asset, defang=True):
            raw.append(asset)
    seen = set()
    unique = []
    for a in raw:
        key = a.lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


def collect_project_indicators(project, items) -> list[str]:
    """
    Returns unique defanged malicious indicators from the project overview and evidence items.
    """
    raw = split_to_bullet_items(project.key_malicious_indicators, defang=True)
    for item in items:
        for ind in split_to_bullet_items(item.malicious_hosts_ips, defang=True):
            raw.append(ind)
    seen = set()
    unique = []
    for i in raw:
        key = i.lower()
        if key not in seen:
            seen.add(key)
            unique.append(i)
    return unique


def collect_mitre_summary(items) -> list[dict]:
    """
    Aggregates MITRE ATT&CK Tactics and Techniques across evidence items
    for the summary table at the end of the report.
    """
    seen = {}
    for item in items:
        tactic = (item.mitre_tactic or "").strip()
        technique = (item.mitre_technique or "").strip()
        if not tactic and not technique:
            continue
        key = (tactic, technique)
        if key not in seen:
            seen[key] = {
                "tactic": tactic or "Unspecified Tactic",
                "technique": technique or "Unspecified Technique",
                "count": 0,
                "assets": set(),
            }
        seen[key]["count"] += 1
        if item.affected_asset:
            seen[key]["assets"].add(defang_text(item.affected_asset.strip()))
    summary = []
    for val in seen.values():
        summary.append({
            "tactic": val["tactic"],
            "technique": val["technique"],
            "count": val["count"],
            "assets": sorted(val["assets"]),
        })
    return summary


def generate_timeline_csv(project) -> tuple[str, Path]:
    """
    Report One:
    Generates an evidence timeline report in CSV format including ALL provided evidence,
    ordered in time series. Only affected assets and malicious indicators/commands are defanged;
    analyst links and notes remain intact.
    """
    evidence_items = project.get_timeline_evidence()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Sequence #",
        "Key Evidence",
        "Timestamp (Start / Event Time UTC)",
        "End Timestamp (UTC)",
        "Evidence Type",
        "Analyst",
        "Affected Asset (Defanged)",
        "Affected User",
        "Attacker-Created User",
        "Summary of Evidence",
        "Analyst Notes",
        "Key Malicious Indicators (Defanged)",
        "Commands Run (Defanged)",
        "MITRE Tactic",
        "MITRE Technique",
        "Evidence Links",
        "Screenshots",
    ])

    for idx, item in enumerate(evidence_items, start=1):
        screenshot_names = ", ".join(
            [os.path.basename(s.image.name) for s in item.screenshots.all()]
        )
        links_str = " | ".join(_collect_links(item))
        writer.writerow([
            idx,
            "Yes" if item.is_key_evidence else "No",
            item.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if item.timestamp else "",
            item.end_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if item.end_timestamp else "",
            item.get_evidence_type_display(),
            item.analyst_name or "",
            defang_text(item.affected_asset),
            item.affected_user,
            "YES" if item.user_created_by_attacker else "NO",
            item.summary,
            item.notes,
            defang_text(item.malicious_hosts_ips),
            defang_text(item.commands_run),
            item.mitre_tactic,
            item.mitre_technique,
            links_str,
            screenshot_names,
        ])

    csv_content = output.getvalue()
    folder_name = project.get_or_create_artifact_folder()
    report_path = (
        Path(settings.ARTIFACTS_ROOT)
        / folder_name
        / "reports"
        / f"evidence_timeline_project_{project.pk}.csv"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(csv_content, encoding="utf-8")

    return csv_content, report_path


def generate_key_evidence_odt(project) -> tuple[bytes, Path]:
    """
    Report Two (OpenDocument Text .odt):
    Structure:
      TITLE
      Summary of incident.
      Key Evidence timeline (each item starts directly with TIMESTAMP, ASSET, USER:)
        Analyst notes.
        Key malicious indicators (defanged)
        Screenshot.
        Links (not defanged).
      Summary at the bottom in Table format:
        - Key assets affected (Table)
        - Key malicious indicators (Table)
        - MITRE tactics and techniques (Table)
    """
    doc = OpenDocumentText()

    h1_style = Style(name="Heading1Custom", family="paragraph")
    h1_style.addElement(ParagraphProperties(marginbottom="0.14in", margintop="0.1in"))
    h1_style.addElement(TextProperties(fontsize="16pt", fontweight="bold"))
    doc.styles.addElement(h1_style)

    h2_style = Style(name="Heading2Custom", family="paragraph")
    h2_style.addElement(ParagraphProperties(marginbottom="0.1in", margintop="0.18in"))
    h2_style.addElement(TextProperties(fontsize="13pt", fontweight="bold"))
    doc.styles.addElement(h2_style)

    h3_style = Style(name="Heading3Custom", family="paragraph")
    h3_style.addElement(ParagraphProperties(marginbottom="0.06in", margintop="0.14in"))
    h3_style.addElement(TextProperties(fontsize="11pt", fontweight="bold"))
    doc.styles.addElement(h3_style)

    body_style = Style(name="BodyCustom", family="paragraph")
    body_style.addElement(ParagraphProperties(marginbottom="0.06in"))
    body_style.addElement(TextProperties(fontsize="10.5pt"))
    doc.styles.addElement(body_style)

    bold_span = Style(name="BoldSpan", family="text")
    bold_span.addElement(TextProperties(fontweight="bold"))
    doc.automaticstyles.addElement(bold_span)

    frame_style = Style(name="ScreenshotFrame", family="graphic")
    frame_style.addElement(GraphicProperties())
    doc.automaticstyles.addElement(frame_style)

    th_cell_style = Style(name="TableHeaderCell", family="table-cell")
    th_cell_style.addElement(
        TableCellProperties(backgroundcolor="#d9e2f3", padding="0.06in", border="0.5pt solid #888888")
    )
    doc.automaticstyles.addElement(th_cell_style)

    td_cell_style = Style(name="TableDataCell", family="table-cell")
    td_cell_style.addElement(
        TableCellProperties(padding="0.06in", border="0.5pt solid #cccccc")
    )
    doc.automaticstyles.addElement(td_cell_style)

    def add_line(label: str, value: str):
        p = P(stylename=body_style)
        p.addElement(Span(stylename=bold_span, text=f"{label}: "))
        p.addText(value)
        doc.text.addElement(p)

    def add_odf_table(table_name: str, headers: list[str], rows: list[list[str]]):
        table = OdfTable(name=table_name)
        for _ in headers:
            table.addElement(TableColumn())

        # Header row
        tr_head = TableRow()
        for h_text in headers:
            tc = TableCell(stylename=th_cell_style, valuetype="string")
            p = P(stylename=body_style)
            p.addElement(Span(stylename=bold_span, text=h_text))
            tc.addElement(p)
            tr_head.addElement(tc)
        table.addElement(tr_head)

        # Data rows
        if not rows:
            tr_empty = TableRow()
            for idx in range(len(headers)):
                tc = TableCell(stylename=td_cell_style, valuetype="string")
                tc.addElement(P(stylename=body_style, text="None recorded" if idx == 0 else "—"))
                tr_empty.addElement(tc)
            table.addElement(tr_empty)
        else:
            for row in rows:
                tr = TableRow()
                for cell_val in row:
                    tc = TableCell(stylename=td_cell_style, valuetype="string")
                    tc.addElement(P(stylename=body_style, text=str(cell_val or "—")))
                    tr.addElement(tc)
                table.addElement(tr)

        doc.text.addElement(table)
        doc.text.addElement(P(stylename=body_style, text=""))

    # 1. TITLE
    title_text = project.title or f"Incident #{project.pk}"
    doc.text.addElement(H(outlinelevel=1, stylename=h1_style, text=title_text))

    # 2. Summary of incident
    doc.text.addElement(H(outlinelevel=2, stylename=h2_style, text="Summary of Incident"))
    doc.text.addElement(
        P(stylename=body_style, text=project.summary or "No summary of incident recorded.")
    )

    # 3. Key Evidence Timeline
    doc.text.addElement(H(outlinelevel=2, stylename=h2_style, text="Key Evidence Timeline"))

    all_items = list(project.get_timeline_evidence())
    key_items = [item for item in all_items if item.is_key_evidence]

    if not key_items:
        doc.text.addElement(P(stylename=body_style, text="No items flagged as Key Evidence."))
    else:
        for item in key_items:
            ts_str = _format_timestamp_range(item)
            asset_str = defang_text(item.affected_asset) or "N/A"
            user_str = item.affected_user or "N/A"
            if item.user_created_by_attacker:
                user_str += " (Created by Attacker)"

            # Item header starts directly with TIMESTAMP, ASSET, USER:
            doc.text.addElement(
                H(
                    outlinelevel=3,
                    stylename=h3_style,
                    text=f"{ts_str}, {asset_str}, {user_str}:",
                )
            )

            # Analyst notes
            add_line("Analyst notes", _format_analyst_notes(item))

            # Key malicious indicators (defanged)
            indicators = _collect_key_indicators(item)
            if indicators:
                p_ind = P(stylename=body_style)
                p_ind.addElement(Span(stylename=bold_span, text="Key malicious indicators:"))
                doc.text.addElement(p_ind)
                odf_list = List()
                for ind in indicators:
                    li = ListItem()
                    li.addElement(P(stylename=body_style, text=ind))
                    odf_list.addElement(li)
                doc.text.addElement(odf_list)
            else:
                add_line("Key malicious indicators", "None")

            # Screenshot
            screenshots = list(item.screenshots.all())
            if screenshots:
                p_shot = P(stylename=body_style)
                p_shot.addElement(Span(stylename=bold_span, text="Screenshot:"))
                doc.text.addElement(p_shot)
                for shot in screenshots:
                    try:
                        img_path = Path(shot.image.path)
                        if img_path.exists():
                            width_in = 5.0
                            height_in = 2.5
                            try:
                                with PilImage.open(img_path) as pil_img:
                                    w_px, h_px = pil_img.size
                                    if w_px > 0 and h_px > 0:
                                        aspect = h_px / float(w_px)
                                        width_in = min(5.5, max(2.5, w_px / 130.0))
                                        height_in = round(width_in * aspect, 2)
                            except Exception:
                                pass

                            href = doc.addPicture(str(img_path))
                            p_img = P(stylename=body_style)
                            frame = Frame(
                                stylename=frame_style,
                                width=f"{width_in:.2f}in",
                                height=f"{height_in:.2f}in",
                                anchortype="as-char",
                            )
                            frame.addElement(OdfImage(href=href))
                            p_img.addElement(frame)
                            doc.text.addElement(p_img)
                    except Exception:
                        pass
            else:
                add_line("Screenshot", "None")

            # Links (NOT defanged)
            links = _collect_links(item)
            if links:
                p_links = P(stylename=body_style)
                p_links.addElement(Span(stylename=bold_span, text="Links: "))
                for i, l_url in enumerate(links):
                    if i > 0:
                        p_links.addText(" , ")
                    p_links.addElement(A(href=l_url, text=l_url))
                doc.text.addElement(p_links)
            else:
                add_line("Links", "None")

    # 4. Summary Tables at the Bottom
    doc.text.addElement(H(outlinelevel=2, stylename=h2_style, text="Incident Summary Tables"))

    assets_list = collect_project_assets(project, all_items)
    add_odf_table(
        "KeyAssetsAffectedTable",
        ["Key Assets Affected"],
        [[a] for a in assets_list],
    )

    indicators_list = collect_project_indicators(project, all_items)
    add_odf_table(
        "KeyMaliciousIndicatorsTable",
        ["Key Malicious Indicators"],
        [[ind] for ind in indicators_list],
    )

    mitre_rows = collect_mitre_summary(all_items)
    add_odf_table(
        "MitreTacticsTechniquesTable",
        ["MITRE Tactic", "MITRE Technique", "Affected Assets"],
        [
            [row["tactic"], row["technique"], ", ".join(row["assets"]) or "—"]
            for row in mitre_rows
        ],
    )

    buf = io.BytesIO()
    doc.write(buf)
    odt_bytes = buf.getvalue()

    folder_name = project.get_or_create_artifact_folder()
    report_path = (
        Path(settings.ARTIFACTS_ROOT)
        / folder_name
        / "reports"
        / f"key_evidence_report_project_{project.pk}.odt"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(odt_bytes)

    return odt_bytes, report_path


def generate_key_evidence_markdown(project) -> tuple[str, Path, bytes]:
    """
    Report Two (Markdown + dedicated screenshots folder):
    Follows the exact structure:
      TITLE
      Summary of incident.
      Key Evidence timeline (starting directly with TIMESTAMP, ASSET, USER:)
      Summary tables at the bottom (Key assets affected, Key malicious indicators, MITRE tactics and techniques).
    """
    folder_name = project.get_or_create_artifact_folder()
    reports_dir = Path(settings.ARTIFACTS_ROOT) / folder_name / "reports"
    screenshots_subdir_name = f"key_evidence_screenshots_project_{project.pk}"
    screenshots_dir = reports_dir / screenshots_subdir_name
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    title_text = project.title or f"Incident #{project.pk}"
    lines = [
        f"# {title_text}",
        "",
        "## Summary of Incident",
        "",
        project.summary or "No summary of incident recorded.",
        "",
        "## Key Evidence Timeline",
        "",
    ]

    all_items = list(project.get_timeline_evidence())
    key_items = [item for item in all_items if item.is_key_evidence]

    copied_files: list[Path] = []

    if not key_items:
        lines.append("No items flagged as Key Evidence.")
        lines.append("")
    else:
        for item in key_items:
            ts_str = _format_timestamp_range(item)
            asset_str = defang_text(item.affected_asset) or "N/A"
            user_str = item.affected_user or "N/A"
            if item.user_created_by_attacker:
                user_str += " (Created by Attacker)"

            lines.extend([
                f"### {ts_str}, {asset_str}, {user_str}:",
                "",
                f"**Analyst notes:** {_format_analyst_notes(item)}",
                "",
                "**Key malicious indicators:**",
            ])

            indicators = _collect_key_indicators(item)
            if indicators:
                for ind in indicators:
                    lines.append(f"- {ind}")
            else:
                lines.append("- None")
            lines.append("")

            lines.append("**Screenshot:**")
            screenshots = list(item.screenshots.all())
            if screenshots:
                for shot in screenshots:
                    src_path = Path(shot.image.path)
                    safe_name = os.path.basename(shot.image.name)
                    dest_path = screenshots_dir / safe_name
                    if src_path.exists():
                        shutil.copy2(src_path, dest_path)
                        copied_files.append(dest_path)
                    caption = shot.caption or safe_name
                    lines.append(f"![{caption}](./{screenshots_subdir_name}/{safe_name})")
            else:
                lines.append("None")
            lines.append("")

            links = _collect_links(item)
            lines.append("**Links:**")
            if links:
                for link in links:
                    lines.append(f"- {link}")
            else:
                lines.append("- None")
            lines.append("")

    # Bottom Summary Tables
    lines.extend([
        "## Summary",
        "",
        "### Key Assets Affected",
        "",
        "| Key Assets Affected |",
        "| --- |",
    ])
    assets_list = collect_project_assets(project, all_items)
    if assets_list:
        for a in assets_list:
            lines.append(f"| {a} |")
    else:
        lines.append("| None recorded |")

    lines.extend([
        "",
        "### Key Malicious Indicators",
        "",
        "| Key Malicious Indicators |",
        "| --- |",
    ])
    indicators_list = collect_project_indicators(project, all_items)
    if indicators_list:
        for ind in indicators_list:
            lines.append(f"| {ind} |")
    else:
        lines.append("| None recorded |")

    lines.extend([
        "",
        "### MITRE Tactics and Techniques",
        "",
        "| MITRE Tactic | MITRE Technique | Affected Assets |",
        "| --- | --- | --- |",
    ])
    mitre_rows = collect_mitre_summary(all_items)
    if mitre_rows:
        for row in mitre_rows:
            assets_str = ", ".join(row["assets"]) if row["assets"] else "—"
            lines.append(f"| {row['tactic']} | {row['technique']} | {assets_str} |")
    else:
        lines.append("| None recorded | — | — |")
    lines.append("")

    md_content = "\n".join(lines)
    report_path = reports_dir / f"key_evidence_report_project_{project.pk}.md"
    report_path.write_text(md_content, encoding="utf-8")

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(report_path.name, md_content)
        for file_path in copied_files:
            zf.write(file_path, arcname=f"{screenshots_subdir_name}/{file_path.name}")
    zip_bytes = zip_buf.getvalue()
    zip_path = reports_dir / f"key_evidence_markdown_project_{project.pk}.zip"
    zip_path.write_bytes(zip_bytes)

    return md_content, report_path, zip_bytes

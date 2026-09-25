"""Synthetic PDF & TXT Document Generator.

Compiles HTML templates from templates/ into realistic, multi-page PDF and text documents
in data/documents/ matching the exact requirements in PRD §3.2.2.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from utils.config import resolve_path, load_config


def strip_html_tags(text: str) -> str:
    """Strip basic HTML tags for plain text rendering."""
    clean = re.sub(r"<[^>]+>", "", text)
    return clean.strip()


def render_html_to_pdf(html_content: str, output_pdf_path: Path):
    """Convert template HTML content into a clean PDF document using ReportLab."""
    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=8,
    )

    story = []

    # Simple line-by-line / tag parser for structured flow
    lines = html_content.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("<h1>") and line.endswith("</h1>"):
            title = strip_html_tags(line)
            story.append(Paragraph(title, title_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=10))
        elif line.startswith("<h2>") and line.endswith("</h2>"):
            heading = strip_html_tags(line)
            story.append(Paragraph(heading, h2_style))
        elif line.startswith("<p>") or line.endswith("</p>"):
            text = line.replace("<p>", "").replace("</p>", "").strip()
            if text:
                # Basic inline tags supported by ReportLab Paragraph: <b>, <i>, <strong>
                story.append(Paragraph(text, body_style))
        elif line.startswith("<li>") and line.endswith("</li>"):
            text = "• " + strip_html_tags(line)
            story.append(Paragraph(text, body_style))

    doc.build(story)


def generate_all_documents():
    cfg = load_config()
    docs_dir = resolve_path(cfg["paths"]["documents_dir"])
    templates_dir = resolve_path(cfg["paths"]["templates_dir"])
    docs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Vendor MSAs
    msa_template_path = templates_dir / "msa_template.html"
    with open(msa_template_path, "r", encoding="utf-8") as f:
        msa_tpl = f.read()

    vendor_msas = [
        {
            "filename": "Supermicro_GPU_Nodes_MSA.pdf",
            "vars": {
                "TITLE": "Supermicro Master Service Agreement 2026",
                "DOC_ID": "MSA-SM-2026-V1.2",
                "VERSION": "1.2",
                "EFFECTIVE_DATE": "2026-01-15",
                "SUPPLIER_NAME": "Super Micro Computer, Inc. (San Jose, CA)",
                "COVERED_COMPONENTS": "SKU-CHAS-ORV3-SM (ORV3 8U GPU Chassis Modules) and associated HGX/OAM carrier boards",
                "LEAD_TIME_WEEKS": "14",
            },
        },
        {
            "filename": "Wiwynn_Chassis_MSA.pdf",
            "vars": {
                "TITLE": "Wiwynn Chassis & Rack Supply Agreement",
                "DOC_ID": "MSA-WI-2025-V1.0",
                "VERSION": "1.0",
                "EFFECTIVE_DATE": "2025-11-01",
                "SUPPLIER_NAME": "Wiwynn Corporation (Taipei, Taiwan)",
                "COVERED_COMPONENTS": "SKU-CHAS-ORV3-WI (Wiwynn ORV3 4OU Compute Sleds)",
                "LEAD_TIME_WEEKS": "12",
            },
        },
        {
            "filename": "Eviden_BullSequana_Contract.pdf",
            "vars": {
                "TITLE": "Eviden BullSequana High Performance Server Contract",
                "DOC_ID": "CTR-EVI-2025-V2.1",
                "VERSION": "2.1",
                "EFFECTIVE_DATE": "2025-12-10",
                "SUPPLIER_NAME": "Eviden International / Atos Group (Bezons, France)",
                "COVERED_COMPONENTS": "SKU-CHAS-EVIDEN-BULL (BullSequana XH3000 Server Blades) and SKU-SEC-HSM-SOV",
                "LEAD_TIME_WEEKS": "16",
            },
        },
        {
            "filename": "Submer_Cooling_Agreement.pdf",
            "vars": {
                "TITLE": "Submer Immersion Cooling Systems SLA & Supply Agreement",
                "DOC_ID": "SLA-SUB-2025-V1.1",
                "VERSION": "1.1",
                "EFFECTIVE_DATE": "2025-10-15",
                "SUPPLIER_NAME": "Submer Technologies SL (Barcelona, Spain)",
                "COVERED_COMPONENTS": "SKU-MAN-SUBMER-01 (SmartPod Immersion Cooling Manifold v3) and dielectric fluid heat exchangers",
                "LEAD_TIME_WEEKS": "16",
            },
        },
    ]

    for item in vendor_msas:
        content = msa_tpl
        for k, v in item["vars"].items():
            content = content.replace(f"{{{{{k}}}}}", v)

        pdf_path = docs_dir / item["filename"]
        txt_path = docs_dir / item["filename"].replace(".pdf", ".txt")
        render_html_to_pdf(content, pdf_path)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(strip_html_tags(content))

    # 2. Technical Specs
    spec_template_path = templates_dir / "tech_spec_template.html"
    with open(spec_template_path, "r", encoding="utf-8") as f:
        spec_tpl = f.read()

    tech_specs = [
        {
            "filename": "OCP_ORV3_Rack_Standard.pdf",
            "vars": {
                "TITLE": "Open Compute Project: Open Rack v3 (ORV3) Base Standard",
                "DOC_ID": "SPEC-OCP-ORV3-V3.0",
                "VERSION": "3.0",
                "AUTHOR": "Open Compute Project Foundation (OCP Hardware Management Working Group)",
                "OVERVIEW_TEXT": "The ORV3 base standard defines mechanical, electrical, and thermal parameters for 21-inch sovereign open racks operating at 48V DC busbar distribution, supporting up to 48kW load per rack with blind-mate liquid cooling connectors.",
            },
        },
        {
            "filename": "AMD_MI300X_Deployment_Guide.pdf",
            "vars": {
                "TITLE": "AMD Instinct MI300X Accelerator Architecture & Deployment Guide",
                "DOC_ID": "SPEC-AMD-MI300X-V1.4",
                "VERSION": "1.4",
                "AUTHOR": "AMD Enterprise AI Architecture Group (Austin, TX)",
                "OVERVIEW_TEXT": "The AMD Instinct MI300X accelerator delivers 192GB HBM3 memory with 5.3TB/s peak bandwidth per OAM module, rated at 750W TDP. It requires ROCm 6.2 or 6.3 kernel drivers and supports native PyTorch execution for Mistral-Large and Llama-3-70B without proprietary CUDA dependencies.",
            },
        },
        {
            "filename": "RoCEv2_Network_Fabric_Spec.pdf",
            "vars": {
                "TITLE": "RoCEv2 800G Data Center AI Fabric Architecture Specification",
                "DOC_ID": "SPEC-ROCE-800G-V2.0",
                "VERSION": "2.0",
                "AUTHOR": "Ultra Ethernet & Sovereign Networking Alliance",
                "OVERVIEW_TEXT": "Defines lossless RDMA over Converged Ethernet (RoCEv2) for 800Gb/s spine-leaf topologies powered by Broadcom Tomahawk 5 (SKU-SW-TH5) switching silicon and PAM4 OSFP optical transceivers.",
            },
        },
    ]

    for item in tech_specs:
        content = spec_tpl
        for k, v in item["vars"].items():
            content = content.replace(f"{{{{{k}}}}}", v)

        pdf_path = docs_dir / item["filename"]
        txt_path = docs_dir / item["filename"].replace(".pdf", ".txt")
        render_html_to_pdf(content, pdf_path)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(strip_html_tags(content))

    # 3. Compliance & Audit
    comp_template_path = templates_dir / "compliance_template.html"
    with open(comp_template_path, "r", encoding="utf-8") as f:
        comp_tpl = f.read()

    compliance_docs = [
        {
            "filename": "BSI_C5_Sovereignty_Attestation.pdf",
            "vars": {
                "TITLE": "BSI C5:2024 Sovereign Cloud Security & Attestation Report",
                "DOC_ID": "AUD-BSI-C5-2024-01",
                "VERSION": "2024.1",
                "EFFECTIVE_DATE": "2025-01-10",
                "AUTHORITY": "TÜV Informationstechnik GmbH & German Federal Office for Information Security (BSI)",
                "COMPLIANCE_SUMMARY": "Aethelgard DC-1 Frankfurt am Main has passed all 17 criteria domains of the BSI Cloud Computing Compliance Criteria Catalogue (C5:2024), certifying strict sovereign data residency and physical operational autonomy within Germany.",
            },
        },
        {
            "filename": "EU_AI_Act_Conformity_Statement.pdf",
            "vars": {
                "TITLE": "EU AI Act Sovereign Compute Infrastructure Conformity Statement",
                "DOC_ID": "AUD-EU-AIA-2025-01",
                "VERSION": "1.0",
                "EFFECTIVE_DATE": "2025-07-01",
                "AUTHORITY": "European Artificial Intelligence Board Notified Body",
                "COMPLIANCE_SUMMARY": "Confirms conformity with Regulation (EU) 2024/1689 (EU AI Act) for high-risk compute deployments. Asserts data governance compliance, hardware root-of-trust isolation, and auditability.",
            },
        },
        {
            "filename": "NIS2_Supply_Chain_Security_Policy.pdf",
            "vars": {
                "TITLE": "NIS2 Critical Infrastructure Supply Chain Security Standard & Policy",
                "DOC_ID": "POL-NIS2-SC-2025-01",
                "VERSION": "1.0",
                "EFFECTIVE_DATE": "2025-05-15",
                "AUTHORITY": "European Union Agency for Cybersecurity (ENISA) & German BSI",
                "COMPLIANCE_SUMMARY": "Mandates mandatory cryptographic verification of hardware pedigree, firmware provenance, and supply chain vulnerability assessments pursuant to Directive (EU) 2022/2555.",
            },
        },
    ]

    for item in compliance_docs:
        content = comp_tpl
        for k, v in item["vars"].items():
            content = content.replace(f"{{{{{k}}}}}", v)

        pdf_path = docs_dir / item["filename"]
        txt_path = docs_dir / item["filename"].replace(".pdf", ".txt")
        render_html_to_pdf(content, pdf_path)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(strip_html_tags(content))

    # 4. Disruption Bulletins & PPA
    bull_template_path = templates_dir / "bulletin_template.html"
    with open(bull_template_path, "r", encoding="utf-8") as f:
        bull_tpl = f.read()

    bulletin_docs = [
        {
            "filename": "Taiwan_Strait_Freight_Advisory.pdf",
            "vars": {
                "TITLE": "Geopolitical Freight Risk Advisory: Taiwan Strait Transit Disruptions",
                "DOC_ID": "BUL-GEO-2026-01",
                "CLASSIFICATION": "DISRUPTION_BULLETIN",
                "EFFECTIVE_DATE": "2026-01-20",
                "ISSUER": "Global Maritime Logistics & Sovereign Supply Watch",
                "SITUATION_SUMMARY": "Heightened naval exercises and declared exclusion zones in the Taiwan Strait have caused major container carriers and air freighters to reroute or freeze cargo out of Kaohsiung and Taipei ports.",
                "IMPACTED_COMPONENTS": "Sub-tier wafer fabrication and packaging for AMD MI300X, NVIDIA H200, Broadcom Tomahawk 5, Wiwynn compute sleds, and Delta 48V power shelves.",
                "FORECAST_DETAILS": "Expected lead time delay of +16 weeks on all direct shipments and indirect sub-tier assemblies originating from Taiwan.",
                "PENALTY_CLAUSES": "Carriers have invoked maritime emergency surcharges; buyers advised to assess liquidated damages applicability against Tier-1 vendors.",
                "RECOMMENDED_ACTIONS": "Qualify secondary European assembly partners; activate regional safety stock reserves.",
            },
        },
        {
            "filename": "Red_Sea_Shipping_Disruption_Report.pdf",
            "vars": {
                "TITLE": "Maritime Shipping Disruption Analysis: Suez Canal & Red Sea Transit",
                "DOC_ID": "BUL-MAR-2026-02",
                "CLASSIFICATION": "DISRUPTION_BULLETIN",
                "EFFECTIVE_DATE": "2026-01-05",
                "ISSUER": "International Chamber of Shipping & Baltic Exchange",
                "SITUATION_SUMMARY": "Continued security incidents in the Bab-el-Mandeb strait have forced 85% of container traffic around the Cape of Good Hope.",
                "IMPACTED_COMPONENTS": "Passive components, copper busbars, chassis frames, and cable harnesses traveling from Asian assembly plants to Rotterdam/Hamburg.",
                "FORECAST_DETAILS": "Transit times increased by 14 to 21 calendar days with container freight rate spikes of 220%.",
                "PENALTY_CLAUSES": "Incoterms DDP obligations require suppliers to absorb freight surcharges unless specific contractual rider exists.",
                "RECOMMENDED_ACTIONS": "Shift critical sub-assemblies to air cargo under expedited customs corridors.",
            },
        },
        {
            "filename": "District_Heating_PPA.pdf",
            "vars": {
                "TITLE": "Frankfurt Municipal District Heating Waste Heat Export Power Purchase Agreement",
                "DOC_ID": "PPA-FFM-HEAT-2025-01",
                "CLASSIFICATION": "LEGAL_COMMERCIAL",
                "EFFECTIVE_DATE": "2025-04-01",
                "ISSUER": "Mainova AG (Frankfurt Municipal Utility) & Aethelgard DC-1",
                "SITUATION_SUMMARY": "Binding energy partnership under the German Energy Efficiency Act (EnEfG). Aethelgard DC-1 commits to exporting continuous waste thermal energy into the Frankfurt municipal district heating network.",
                "IMPACTED_COMPONENTS": "Primary Coolant Loop Pump B (SKU-PUMP-HALL1-B), Kelvion heat exchangers, and secondary Loop-A liquid cooling loops.",
                "FORECAST_DETAILS": "Minimum continuous thermal export target: 12.5 MW thermal at minimum 58°C supply temperature.",
                "PENALTY_CLAUSES": "Under Section 8.4 (Thermal Export Default), if an unexcused cooling loop shutdown causes thermal supply to fall below 60% of baseline for more than 4 consecutive hours, Aethelgard shall pay liquidated damages of €45,000 per 24-hour period to Mainova AG.",
                "RECOMMENDED_ACTIONS": "Maintain redundant N+1 cooling pump failover and backup heat dump radiators.",
            },
        },
        {
            "filename": "US_Export_Control_Update.pdf",
            "vars": {
                "TITLE": "US BIS Advanced Compute & Semiconductor Export Controls Regulatory Briefing",
                "DOC_ID": "BUL-REG-2025-04",
                "CLASSIFICATION": "DISRUPTION_BULLETIN",
                "EFFECTIVE_DATE": "2025-10-30",
                "ISSUER": "US Department of Commerce, Bureau of Industry and Security (BIS)",
                "SITUATION_SUMMARY": "Updated Export Administration Regulations (EAR) tightening Total Processing Performance (TPP) and performance density thresholds for advanced AI accelerators.",
                "IMPACTED_COMPONENTS": "NVIDIA H200 (SKU-GPU-H200), high-density optical switches, and wafer-level testing equipment.",
                "FORECAST_DETAILS": "Mandatory end-user licensing required for non-EU entities. Inspur Systems placed on Entity List (Sanctioned status).",
                "PENALTY_CLAUSES": "Civil and criminal penalties under EAR for unauthorized secondary re-export or diversion.",
                "RECOMMENDED_ACTIONS": "Prioritize European sovereign hardware and AMD ROCm open infrastructure stacks.",
            },
        },
    ]

    for item in bulletin_docs:
        content = bull_tpl
        for k, v in item["vars"].items():
            content = content.replace(f"{{{{{k}}}}}", v)

        pdf_path = docs_dir / item["filename"]
        txt_path = docs_dir / item["filename"].replace(".pdf", ".txt")
        render_html_to_pdf(content, pdf_path)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(strip_html_tags(content))

    print(f"Generated 14 PDF and 14 TXT documents in {docs_dir}")


if __name__ == "__main__":
    generate_all_documents()

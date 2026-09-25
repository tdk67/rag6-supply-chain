"""Automated Playwright Script to capture authentic UI screenshots of Aethelgard Infra-GraphRAG.

Captures all 4 primary operational tabs in the running Streamlit application:
1. Tab 1: AI Decision Console (with live chat response, citations, confidence badge)
2. Tab 2: Simulation & Data Studio (with Scenario A applied and live BOM preview)
3. Tab 3: Knowledge Base Analytics (with KPIs, supplier risk chart, and discrepancy audit)
4. Tab 4: Ingestion & Lifecycle Manager (with upload zone, collection metrics, and preview)
"""

from __future__ import annotations

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def capture_all_tabs():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 960},
            device_scale_factor=2,  # Crisp high-DPI rendering
        )
        page = context.new_page()

        print("Navigating to Streamlit app at http://localhost:8501...")
        page.goto("http://localhost:8501", timeout=30000)
        page.wait_for_selector(".main-header", timeout=20000)
        time.sleep(2)

        tabs = page.get_by_role("tab")
        tab_count = tabs.count()
        print(f"Detected {tab_count} Streamlit tabs.")

        # -------------------------------------------------------------
        # 1. Capture Tab 1: AI Decision Console
        # -------------------------------------------------------------
        print("Capturing Tab 1: AI Decision Console...")
        tabs.nth(0).click()
        time.sleep(1)

        # Trigger Q3 Benchmark Question or submit chat input
        try:
            chat_input = page.locator("textarea[data-testid='stChatInputTextArea']")
            if chat_input.is_visible():
                q_text = "If geopolitical conflict disrupts freight routes out of Taiwan, which Tier-1 hardware components are directly or indirectly blocked, which sub-tier suppliers are the bottlenecks, and what is our total affected order value?"
                chat_input.fill(q_text)
                chat_input.press("Enter")
                print("Submitted Q1 prompt into chat input...")

                # Wait for assistant response to render
                page.wait_for_selector("div[data-testid='stChatMessage']:nth-child(2)", timeout=60000)
                print("Assistant response received!")
                time.sleep(6)  # Allow charts and citations to settle
        except Exception as e:
            print(f"Notice during Tab 1 chat execution: {e}")

        # Capture Tab 1
        page.screenshot(path=str(OUTPUT_DIR / "ui_decision_console.png"), full_page=False)
        print("Saved ui_decision_console.png")

        # -------------------------------------------------------------
        # 2. Capture Tab 2: Simulation & Data Studio
        # -------------------------------------------------------------
        print("Capturing Tab 2: Simulation & Data Studio...")
        tabs.nth(1).click()
        time.sleep(2)

        try:
            # Click Scenario A radio button
            scenario_a = page.locator("label").filter(has_text="Scenario A: Taiwan Freight Embargo")
            if scenario_a.is_visible():
                scenario_a.click()
                time.sleep(0.5)

            # Click Apply Scenario button
            apply_btn = page.locator("button").filter(has_text="Apply Scenario to Infrastructure")
            if apply_btn.is_visible():
                apply_btn.click()
                print("Applied Scenario A...")
                time.sleep(4)
        except Exception as e:
            print(f"Notice during Tab 2 action: {e}")

        page.screenshot(path=str(OUTPUT_DIR / "ui_simulation_studio.png"), full_page=False)
        print("Saved ui_simulation_studio.png")

        # -------------------------------------------------------------
        # 3. Capture Tab 3: Knowledge Base Analytics
        # -------------------------------------------------------------
        print("Capturing Tab 3: Knowledge Base Analytics...")
        tabs.nth(2).click()
        time.sleep(4)  # Allow charts and dataframes to render

        page.screenshot(path=str(OUTPUT_DIR / "ui_analytics_dashboard.png"), full_page=False)
        print("Saved ui_analytics_dashboard.png")

        # -------------------------------------------------------------
        # 4. Capture Tab 4: Ingestion & Lifecycle
        # -------------------------------------------------------------
        print("Capturing Tab 4: Ingestion & Lifecycle...")
        tabs.nth(3).click()
        time.sleep(3)

        page.screenshot(path=str(OUTPUT_DIR / "ui_ingestion_lifecycle.png"), full_page=False)
        print("Saved ui_ingestion_lifecycle.png")

        browser.close()
        print("All authentic screenshots successfully captured!")


if __name__ == "__main__":
    capture_all_tabs()

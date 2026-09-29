import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = "/config/.gemini/antigravity/brain/ec3e3fa9-0dc3-49e0-86ed-a1372661fe71"
FRONTEND_URL = "https://globetrotter-frontend-982946819912.us-east1.run.app"

def run():
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    temp_video_dir = os.path.join(ARTIFACT_DIR, "video_temp")
    os.makedirs(temp_video_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=temp_video_dir,
            record_video_size={"width": 1280, "height": 720}
        )
        page = context.new_page()

        print(f"Navigating to {FRONTEND_URL}...")
        page.goto(FRONTEND_URL)
        page.wait_for_selector("#log", timeout=10000)
        time.sleep(3)

        # First prompt: Click 3-Day Tokyo Itinerary prompt chip
        print("Sending prompt 1: Tokyo Itinerary...")
        chip = page.query_selector(".prompt-chip")
        if chip:
            chip.click()
        else:
            page.fill("#input", "Plan a 3-day itinerary in Tokyo with local food options")
            page.click("button.send-btn")

        # Wait for agent response (looking for response bubble after user message)
        time.sleep(15)

        # Second prompt: Generate image tool call
        print("Sending prompt 2: Generate domain image...")
        page.fill("#input", "Generate an image of a delicious bowl of authentic Tokyo tonkotsu ramen for my travel guide.")
        page.click("button.send-btn")

        # Wait for image generation tool execution, GCS upload, and response rendering
        time.sleep(22)

        print("Finished demo interactions. Closing context...")
        page_video = page.video
        context.close()
        browser.close()

        if page_video:
            video_path = page_video.path()
            target_path = os.path.join(ARTIFACT_DIR, "demo_video.webm")
            print(f"Video saved to: {video_path}")
            os.rename(video_path, target_path)
            print(f"Moved video to artifact destination: {target_path}")

if __name__ == "__main__":
    run()

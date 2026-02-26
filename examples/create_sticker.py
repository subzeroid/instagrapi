from instagrapi import Client
import os

USERNAME = os.environ.get("IG_USERNAME")
PASSWORD = os.environ.get("IG_PASSWORD")

cl = Client()
cl.login(USERNAME, PASSWORD)

# Path to your image (transparent PNG or solid JPG)
image_path = "path/to/your/image.jpg"

print(f"Uploading {image_path} as a Cutout Sticker...")

# 1. Bypass AI (Full Image) - Recommended for pre-cut images
sticker = cl.photo_upload_to_cutout_sticker(image_path, bypass_ai=True)
print(f"Sticker Created (Manual Box)! ID: {sticker.pk}")

# 2. Use AI (Instagram Server-Side Segmentation)
# sticker_ai = cl.photo_upload_to_cutout_sticker(image_path, bypass_ai=False)
# print(f"Sticker Created (AI)! ID: {sticker_ai.pk}")
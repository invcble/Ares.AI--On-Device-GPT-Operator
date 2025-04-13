import base64
import os
import json
from gem_orch import process_request  # your full logic lives here

# Setup test inputs
instruction = "Open WhatsApp and send text message to Subhrato Som"
client_id = "test_client"

# Folder with mock screenshots
mock_folder = "content"
image_files = sorted(os.listdir(mock_folder))  # assumes 1.jpeg, 2.jpeg, ...

# Step 1: send instruction + first screenshot
def encode_image(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

first_image_path = os.path.join(mock_folder, image_files[0])
first_payload = {
    "instruction": instruction,
    "imageb64": encode_image(first_image_path)
}

# Send first input
print(">>> First request:")
response = process_request(first_payload, client_id)
print(json.dumps(response, indent=2))

# Step 2 onward: send remaining screenshots one at a time
for image_name in image_files[1:]:
    path = os.path.join(mock_folder, image_name)
    payload = {
        "imageb64": encode_image(path)
    }
    print(f"\n>>> Processing {image_name}:")
    response = process_request(payload, client_id)
    print(json.dumps(response, indent=2))

    if response.get("isDone"):
        print("✅ Instruction completed!")
        break

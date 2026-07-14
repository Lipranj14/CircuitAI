import json
import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
# URL of the endpoint
url = "/api/v1/pipeline/analyze"

# Path to the sample image
image_path = "../CKT_Images/WradV.jpg"

if __name__ == "__main__":
    try:
        with open(image_path, "rb") as f:
            files = {"file": ("WradV.jpg", f, "image/jpeg")}
            
            print("Sending request to V2 endpoint...")
            start_time = time.time()
            
            # Send the POST request
            response = client.post(url, files=files)
            
            end_time = time.time()
            print(f"Request completed in {end_time - start_time:.2f} seconds.")
            
            # Check the response status
            if response.status_code == 200:
                print("Request successful!")
                data = response.json().get("data", {})
                
                circuit = data.get("circuit", {})
                components = circuit.get("components", [])
                wires = circuit.get("wires", [])
                nodes = circuit.get("nodes", [])
                
                print(f"Components detected: {len(components)}")
                print(f"Wires detected: {len(wires)}")
                print(f"Nodes identified: {len(nodes)}")
                
                # Print a summary of components
                print("\nComponent Summary:")
                for comp in components:
                    print(f" - {comp.get('id')}: {comp.get('type')} (label: {comp.get('label')})")
                
                # Check SVG
                svg = data.get("svg", "")
                print(f"\nSVG output generated: {len(svg)} characters")
                
            else:
                print(f"Request failed with status code: {response.status_code}")
                print(response.text)

    except Exception as e:
        print(f"An error occurred: {e}")

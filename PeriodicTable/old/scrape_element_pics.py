import os
import requests
from bs4 import BeautifulSoup
from marciano.periodictable import Element

# Create a directory "ElementPics" if it does not exist
if not os.path.exists("ElementPics"):
    os.makedirs("ElementPics")

element_names = [Element(i).name for i in range(1, 101)]

for element_name in element_names:
    url = f"https://images-of-elements.com/{element_name.lower()}.php"

    # Send a request to fetch the page
    response = requests.get(url)
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find all images and attempt to select the one matching the specific source pattern
        images = soup.find_all('img')
        if len(images) > 1:  # Check if there are at least two images
            # Targeting the second image specifically
            img_tag = images[1]
            if img_tag['src'].endswith(f"{element_name.lower()}.jpg"):
                img_src = img_tag['src']
                # Ensure the source is an absolute URL
                if not img_src.startswith("http"):
                    img_src = f"https://images-of-elements.com/{img_src}"
                # Download the image
                img_response = requests.get(img_src)
                if img_response.status_code == 200:
                    file_path = os.path.join("ElementPics", f"{element_name}.jpg")
                    # Write the image content to a file
                    with open(file_path, 'wb') as file:
                        file.write(img_response.content)
                else:
                    print(f"Failed to download image for {element_name} from {img_src}")
            else:
                print(f"Image for {element_name} does not match expected filename.")
        else:
            print(f"Not enough images found on the page for {element_name}.")
    else:
        print(f"Failed to fetch page for {element_name}.")

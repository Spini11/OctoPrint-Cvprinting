import os
import requests
from ultralytics import YOLO
import uuid

def CheckImage(image, folder):
    print(folder)
    model = YOLO(os.path.join(folder, 'best.pt'))
    print(folder)
    imageLocation = os.path.join(folder,f'images/{str(uuid.uuid4())}.png')
    print(imageLocation)
    response = requests.get(image)
    if response.status_code == 200:
        with open(imageLocation, 'wb') as f:
            f.write(response.content)
    else:
        return "Failed to download image"
    
    results= model(imageLocation)
    return imageLocation, results
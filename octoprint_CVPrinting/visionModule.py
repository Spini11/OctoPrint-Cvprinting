import os
import requests
from ultralytics import YOLO
import uuid

def CheckImage(image, folder):
    model = YOLO(os.path.join(folder, 'data/best.pt'))
    imageLocation = os.path.join(folder,f'{str(uuid.uuid4())}.png')
    response = requests.get(image)
    if response.status_code == 200:
        with open(imageLocation, 'wb') as f:
            f.write(response.content)
    else:
        return "Failed to download image"
    
    result= model(imageLocation)
    return imageLocation, result
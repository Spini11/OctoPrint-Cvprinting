import os
import requests
from ultralytics import YOLO

def CheckImage(image, folder):
    model = YOLO(os.path.join(folder, 'data/best.pt'))
    response = requests.get(image)
    if response.status_code == 200:
        with open(os.path.join(folder,'image.png'), 'wb') as f:
            f.write(response.content)
    else:
        return "Failed to download image"
    
    result= model(os.path.join(folder,'image.png'))
    # os.remove(os.path.join(folder,'image.png'))
    return result
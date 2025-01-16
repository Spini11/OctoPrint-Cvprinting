import os
import requests
from ultralytics import YOLO
import uuid

def CheckImage(image, folder):
    model = YOLO(os.path.join(folder, 'best.pt'))
    imageLocation = os.path.join(folder,f'images/{str(uuid.uuid4())}.png')
    response = requests.get(image)
    if response.status_code == 200:
        with open(imageLocation, 'wb') as f:
            f.write(response.content)
        try:
            results= model(imageLocation)
        except Exception as e:
            return None, 2
    else:
        return None, 1
    
    resultHighestConfidenceNotOk = {}
    for r in results:
        confidences = r.boxes.conf
        class_ids = r.boxes.cls 

        # Iterate through detected boxes
        for conf, cls in zip(confidences, class_ids):
            conf = float(conf)
            label = r.names[int(cls)]
            if label == "PrintOk":
                continue
            elif not resultHighestConfidenceNotOk or conf > resultHighestConfidenceNotOk.get("conf"):
                resultHighestConfidenceNotOk = {"label": label, "conf": conf}

    return imageLocation, resultHighestConfidenceNotOk
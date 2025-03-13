import os
import requests
import uuid
import MNN
import MNN.cv as cv2
import MNN.numpy as np
from PIL import Image


class visionModule:
    config = {}
    model = None
    folder = None

    def __init__(self,  folder):
        self.folder = os.path.join(folder, "data")
        self.model = os.path.join(self.folder, "best.mnn")

        config = {}
        config["precision"] = "medium"
        config["numThread"] = 2 if os.cpu_count() >= 2 else 1
        config["backend"] = "CPU"
        self.config = config

    #Code of the following function was adapted from https://docs.ultralytics.com/integrations/mnn/#mnn-only-inference
    #Original author: UltraLytics, Accesed on 13.3.2025
    def CheckImage(self, img):
        imageLocation = self.getImage(img)
        if imageLocation is None:
            return None, 1
        rt = MNN.nn.create_runtime_manager((self.config,))
        net = MNN.nn.load_module_from_file(self.model, [], [], runtime_manager=rt)
        original_image = cv2.imread(imageLocation)
        if original_image is None:
            return None, 3
        ih, iw, _ = original_image.shape
        length = max((ih, iw))
        scale = length / 640
        image = np.pad(original_image, [[0, length - ih], [0, length - iw], [0, 0]], "constant")
        image = cv2.resize(
            image, (640, 640), 0.0, 0.0, cv2.INTER_LINEAR, -1, [0.0, 0.0, 0.0], [1.0 / 255.0, 1.0 / 255.0, 1.0 / 255.0]
        )
        image = image[..., ::-1]  # BGR to RGB
        input_var = np.expand_dims(image, 0)
        input_var = MNN.expr.convert(input_var, MNN.expr.NC4HW4)
        output_var = net.forward(input_var)
        output_var = MNN.expr.convert(output_var, MNN.expr.NCHW)
        output_var = output_var.squeeze()
        # output_var shape: [84, 8400]; 84 means: [cx, cy, w, h, prob * 80]
        cx = output_var[0]
        cy = output_var[1]
        w = output_var[2]
        h = output_var[3]
        probs = output_var[4:]
        # [cx, cy, w, h] -> [y0, x0, y1, x1]
        x0 = cx - w * 0.5
        y0 = cy - h * 0.5
        x1 = cx + w * 0.5
        y1 = cy + h * 0.5
        boxes = np.stack([x0, y0, x1, y1], axis=1)
        scores = np.max(probs, 0)
        class_ids = np.argmax(probs, 0)
        result_ids = MNN.expr.nms(boxes, scores, 100, 0.45, 0.25)
        # nms result box, score, ids
        result_boxes = boxes[result_ids]
        result_scores = scores[result_ids]
        result_class_ids = class_ids[result_ids]
        return imageLocation, self.convertOuput(result_boxes, result_scores, result_class_ids) 

    def getImage(self, url):
        tmpImageLocation = os.path.join(self.folder,f'images/{str(uuid.uuid4())}.png')
        imageLocation = os.path.join(self.folder,f'images/{str(uuid.uuid4())}.jpg')
        response = requests.get(url)
        if response.status_code == 200:
            try:
                with open(tmpImageLocation, 'wb') as f:
                    f.write(response.content)
                img = Image.open(tmpImageLocation).convert('RGB')
                img.save(imageLocation, format="JPEG")
                os.remove(tmpImageLocation)
                return imageLocation
            except Exception as e:
                print(f"error during image conversion {e}")
                return None
        else:
            return None

    def convertOuput(self, boxes, scores, class_ids):
        resultHighestConfidenceNotOk = {}
        for score, classID in zip(scores, class_ids):
            score_value = int(score.read_as_tuple()[0] * 100)
            classID_value = int(classID.read_as_tuple()[0])
            if classID_value == 0:
                continue
            else:
                if not resultHighestConfidenceNotOk or score_value > resultHighestConfidenceNotOk.get("conf"):
                    resultHighestConfidenceNotOk = {"label": self.getClassName(classID_value), "conf": score_value}
        return resultHighestConfidenceNotOk

    def getClassName(self, class_id):
        names_dict = {
        0: "PrintOk",
        1: "Stringing",
        2: "Spaghetti",
        3: "OverExtrusion",
        4: "UnderExtrusion",
        5: "Gaps",
        6: "PrintNotOk"
        }
        if class_id not in names_dict:
            return "Unknown"
        return names_dict.get(class_id)
        


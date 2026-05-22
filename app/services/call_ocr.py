import pytesseract
import cv2
from PIL import Image

custom_config = '-l jpn+eng --oem 3 --psm 6'

def process_ocr_sync(img_path :str) -> str:
    img = cv2.imread(img_path)
    img_resize = cv2.resize(img, None, fx=2.5, fy= 2.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img_resize, cv2.COLOR_BGR2GRAY)
    blerred = cv2.GaussianBlur(gray,(3,3),0)
    _, thresh = cv2.threshold(blerred, 150, 255, cv2.THRESH_BINARY)
    pil_img = Image.fromarray(thresh)
    text = pytesseract.image_to_string(
        pil_img, 
        config=custom_config
    )
    return text

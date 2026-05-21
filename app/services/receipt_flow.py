## 業務フローのコントロール（手順の統括）などの責務を実行する
## データの具体的な保存・取得コマンド（リポジトリ・インフラの責務）は実施しない
## ex:複数リソースのパイプライン（結合）など

import asyncio
from PIL import Image
import pytesseract
import cv2
# from app.prompts import reate_receipt_prompt
from pathlib import Path
from typing import Any
from fastapi import UploadFile
from app.services.receipt_service import fetch_job_status
from app.repositories.job import JobRepository

img_dir = "../input_img/"
custom_config = '-l jpn+eng --oem 3 --psm 6'
custom_promt = "/prompt/ocr.md"
UPLOAD_DIR = Path("/tmp/receipt_imgs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def init_receipt_pipeline(file_object: UploadFile, job_id:str) -> str:
    await JobRepository.create_job(job_id, {"status": "PENDING"})
    img_path = await save_for_local_receipt_image(file_object, job_id)
    return img_path

# ファイル保存処理、将来的にクラウドに上げることも踏まえた切り出し
async def save_for_local_receipt_image(file_object: UploadFile, job_id:str) -> str:
    saved_file_path = UPLOAD_DIR / f"{job_id}.jpg"
    content = await file_object.read()
    with open(saved_file_path, "wb") as buffer:
        buffer.write(content)
    return str(saved_file_path)

async def view_receipt_status(job_id: str):
	job_status = await fetch_job_status(job_id)
	return job_status


# # 画像の文字列読み込み処理
# def read_text(img_dir):
#   text = convert_img(img_dir)
#   print(text)

# #画像の編集、画像の文字列読み込み
# def convert_img(img_path):
#   img = cv2.imread(img_path)
#   img_resize = cv2.resize(img, None, fx=2.5, fy= 2.5, interpolation=cv2.INTER_CUBIC)
#   gray = cv2.cvtColor(img_resize, cv2.COLOR_BGR2GRAY)
#   blerred = cv2.GaussianBlur(gray,(3,3),0)
#   _, thresh = cv2.threshold(blerred, 150, 255, cv2.THRESH_BINARY)
#   pil_img = Image.fromarray(thresh)
#   print(pil_img)
#   text = pytesseract.image_to_string(
#     pil_img, 
#     config=custom_config
#   )
#   return text

# # json化
# def convert_json(text: str):
#   try:
#     prompt = create_receipt_promp(text)
#     res = self.model.generate_content(prompt)
#     res_text = res.text
#   except Exception as e:
#     return {"error": str(e)}


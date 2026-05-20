from fastapi import UploadFile, File, HTTPException, status

class JPEGValidator:
    def __init__(self, file: UploadFile = File(...)):
        # 1. 拡張子チェック
        filename_lower = file.filename.lower()
        if not (filename_lower.endswith(".jpg") or filename_lower.endswith(".jpeg")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JPG or JPEG files are allowed."
            )
        
        # 2. MIMEタイプチェック
        if file.content_type not in ["image/jpeg", "image/jpg"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JPG or JPEG files are allowed."
            )
        
        # チェックが通ったら、コントローラーで使いやすいように自身に保持
        self.file = file
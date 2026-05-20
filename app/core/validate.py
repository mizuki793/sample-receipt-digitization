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

class costValidator:
    def verify_receipt_total(items: list[dict], total_amount: int) -> tuple[bool, str | None]:
        """
        レシートの各品目の合計金額が、請求総額と一致するか検証する純粋関数。
        
        Returns:
            (True, None) -> 一致している場合
            (False, エラー理由) -> 不一致の場合
        """
        calced_total = sum(item.get("unit_price",0) for item in items) 

        if calced_total != total_amount:
            error_msg = f"金額の不一致を検知しました。各品目の合計: {calced_total}円, 請求総額: {total_amount}円"
            return False, error_msg

        return True, None
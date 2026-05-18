from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def read_root():
  return{"status": "ok"}

# # バッチ処理開始
# @app.post("/v1/receipt/execute")
# def execute_recipt():
#   job_id = "set uniqkey"
#   return {"jon-id": job_id}

# # ジョブ進捗返却(job-idを受け取る)
# @app.get("/v1/jobs/status/{job_id}")
# def view_status_recipt(job_id: int):
#   res_json = {"res-json": "res-json"}
#   return {res_json}
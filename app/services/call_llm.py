import asyncio
import json
import logging
import litellm
from litellm import acompletion

async def call_llm_json(
    prompt: str,
    ai_model: str, 
    max_retries: int = 3, 
    backoff_seconds: int = 60
) -> dict:
    """
    【汎用】指定されたプロンプトとモデルでLLMを呼び出し、結果を辞書型(dict)で返却する。
    429(レートリミット)および500系(サーバーエラー)が発生した場合は、指定秒数待機して自動リトライを行う。
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = await acompletion(
                model=ai_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            raw_json_str = response.choices[0].message.content
            return json.loads(raw_json_str)
        
        except litellm.RateLimitError as e:
            logging.warning(f"[Attempt {attempt}/{max_retries}] Rate limit hit: {str(e)}")
            if attempt == max_retries:
                raise e
            logging.warning(f"Waiting for {backoff_seconds} seconds before retrying...")
            await asyncio.sleep(backoff_seconds)

        except litellm.InternalServerError as e:
            logging.warning(f"[Attempt {attempt}/{max_retries}] LLM Server Error (500/503): {str(e)}")
            if attempt == max_retries:
                raise e
            logging.warning(f"Waiting for {backoff_seconds} seconds before retrying...")
            await asyncio.sleep(backoff_seconds)
          
        except Exception as e:
            logging.error(f"Fatal error during LLM request: {str(e)}")
            raise e

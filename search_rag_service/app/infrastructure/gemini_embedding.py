from google import genai

class GeminiEmbeddingFunction:
    def __init__(self, api_key: str, model_name: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def __call__(self, input: list[str]) -> list[list[float]]:
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=input,
        )
        return [embedding.values for embedding in response.embeddings]

    def embed_documents(self, input: list[str], **kwargs) -> list[list[float]]:
        return self.__call__(input)

    def embed_query(self, input: str | list[str], **kwargs) -> list[float] | list[list[float]]:
        if isinstance(input, str):
            return self.__call__([input])[0]
        return self.__call__(input)

    def name(self) -> str:
        return "GeminiEmbeddingFunction"

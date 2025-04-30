from pydantic import BaseModel

from khive.services.endpoint import Endpoint, EndpointConfig

from .openai_chat import ChatCompletionRequest

_HAS_OLLAMA = True
try:
    import ollama  # type: ignore
except ImportError:
    _HAS_OLLAMA = False


__all__ = ("OllamaChatEndpoint",)


ENDPOINT_CONFIG = EndpointConfig(
    name="ollama_chat",
    provider="ollama",
    base_url="http://localhost:11434/v1",
    endpoint="chat",
    kwargs={"model": "qwen3"},
    openai_compatible=True,
    api_key="mock_key",
    auth_template={"Authorization": "Bearer $API_KEY"},
    default_headers={"content-type": "application/json"},
    request_options=ChatCompletionRequest,
)


class OllamaChatEndpoint(Endpoint):
    """
    Documentation: https://github.com/ollama/ollama/tree/main/docs
    """

    def __init__(self, config=ENDPOINT_CONFIG, **kwargs):
        if not _HAS_OLLAMA:
            raise ImportError(
                "Package `ollama` is required to use the ollama chat endpoint. Please install it via `pip install ollama` and make sure the desktop client is running, to use this feature."
            )

        super().__init__(config, **kwargs)

        from ollama import list as o_list  # type: ignore
        from ollama import pull as o_pull  # type: ignore

        self._pull = o_pull
        self._list = o_list

    @property
    def allowed_roles(self):
        return ["system", "user", "assistant"]

    async def call(
        self, request: dict | BaseModel, cache_control: bool = False, **kwargs
    ):
        payload, _ = self.create_payload(request, **kwargs)
        self._check_model(payload.get("model"))

        return await super().call(
            request=request, cache_control=cache_control, **kwargs
        )

    def _pull_model(self, model: str):
        from tqdm import tqdm

        current_digest, bars = "", {}
        for progress in self._pull(model, stream=True):
            digest = progress.get("digest", "")
            if digest != current_digest and current_digest in bars:
                bars[current_digest].close()

            if not digest:
                print(progress.get("status"))
                continue

            if digest not in bars and (total := progress.get("total")):
                bars[digest] = tqdm(
                    total=total,
                    desc=f"pulling {digest[7:19]}",
                    unit="B",
                    unit_scale=True,
                )

            if completed := progress.get("completed"):
                bars[digest].update(completed - bars[digest].n)

            current_digest = digest

    def _list_local_models(self) -> set:
        response = self._list()
        return {i.model for i in response.models}

    def _check_model(self, model: str):
        if model not in self._list_local_models():
            self._pull_model(model)

class PPUResponse:
    def __init__(self, text: str, sources: list[str], method: str):
        self.text = text
        self.sources = sources
        self.method = method

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "sources": self.sources,
            "method": self.method,
        }

def format_response(text: str, sources: list[str] | None = None, method: str = "template") -> PPUResponse:
    return PPUResponse(text=text, sources=sources or [], method=method)

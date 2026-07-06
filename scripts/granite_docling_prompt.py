"""Shared Granite Docling prompt construction used by inference and fine-tuning."""

PROMPT_TEXT = "Convert this page to docling."


def build_messages() -> list[dict]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": PROMPT_TEXT},
            ],
        },
    ]


def build_prompt(processor) -> str:
    return processor.apply_chat_template(build_messages(), add_generation_prompt=True)

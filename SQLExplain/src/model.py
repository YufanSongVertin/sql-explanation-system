# src/model.py

import os
from dataclasses import dataclass
from typing import Optional

try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
except ImportError as e:
    raise ImportError(
        "transformers and torch are required but not installed.\n"
        "Please run `pip install -r requirements.txt` first."
    ) from e


# Choose a default model unless overridden by environment variable
DEFAULT_MODEL_NAME = os.environ.get(
    "SQLEXPLAIN_MODEL_NAME",
    "google/flan-t5-base",   # default lightweight seq2seq model
)


@dataclass
class SqlExplainModelConfig:
    """
    Configuration for the LLM-based SQL explanation model.
    """
    model_name: str = DEFAULT_MODEL_NAME
    max_new_tokens: int = 256
    temperature: float = 0.3
    device: Optional[str] = None  # "cuda", "cpu", or None for autodetect


class SqlExplainModel:
    """
    Wrapper class for loading a seq2seq model (e.g., FLAN-T5)
    and generating text explanations from prompts.
    """

    def __init__(self, config: Optional[SqlExplainModelConfig] = None):
        if config is None:
            config = SqlExplainModelConfig()
        self.config = config

        # Determine computation device
        if config.device is not None:
            device = config.device
        else:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device

        # Load model and tokenizer
        print(f"[SqlExplainModel] Loading model {config.model_name} on {self.device} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(config.model_name)

        self.model.to(self.device)
        self.model.eval()
        print("[SqlExplainModel] Model loaded.")

    def generate_explanation(self, prompt: str) -> str:
        """
        Generate a text explanation from the input prompt using a seq2seq model.

        Args:
            prompt: Input string for the model.

        Returns:
            A cleaned-up string output produced by the LLM.
        """
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=1024,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.config.max_new_tokens,
                do_sample=True,
                temperature=self.config.temperature,
                top_p=0.95,
            )

        text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return text.strip()

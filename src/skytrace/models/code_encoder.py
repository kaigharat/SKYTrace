"""SkyTrace CodeBERT encoder + classifier head.

Phase-1 baseline: CodeBERT base + 2-layer MLP classifier head for binary
vulnerability detection.

Key design choices:
    - Supports `microsoft/codebert-base` (default) and `microsoft/graphcodebert-base`.
    - Mean-pooling by default (better than [CLS] for code, per Lu et al. 2021).
    - Optional layer freezing for low-resource fine-tuning.
    - Optional embedding cache: when cache_embeddings=true, run CodeBERT once
      on the full dataset, save mean-pooled 768-d vectors to disk, and reuse
      them. The MLP head then trains on cached embeddings — fast on CPU.
    - Mixed-precision (fp16) supported but disabled by default (CPU-only env).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer


@dataclass
class CodeBERTConfig:
    model_name: str = "microsoft/codebert-base"
    hidden_size: int = 768
    freeze_layers: int = 0
    pooling: str = "mean"            # "mean" | "cls" | "max"
    classifier_hidden_dims: list = field(default_factory=lambda: [256])
    dropout: float = 0.1
    n_classes: int = 1               # 1 = binary logistic


class CodeBERTEncoder(nn.Module):
    """Wraps a HuggingFace CodeBERT/GraphCodeBERT model with a pooling head."""

    def __init__(self, cfg: CodeBERTConfig):
        super().__init__()
        self.cfg = cfg
        self.encoder = AutoModel.from_pretrained(cfg.model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)

        # Optional layer freezing
        if cfg.freeze_layers > 0:
            # The encoder has embeddings + N transformer layers
            for p in self.encoder.embeddings.parameters():
                p.requires_grad = False
            for i, layer in enumerate(self.encoder.encoder.layer):
                if i < cfg.freeze_layers:
                    for p in layer.parameters():
                        p.requires_grad = False

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Return pooled (batch_size, hidden_size) embeddings."""
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        last_hidden = out.last_hidden_state        # (B, L, H)

        if self.cfg.pooling == "cls":
            pooled = last_hidden[:, 0, :]
        elif self.cfg.pooling == "max":
            mask = attention_mask.unsqueeze(-1).expand(last_hidden.size()).bool()
            masked = last_hidden.masked_fill(~mask, -1e9)
            pooled = masked.max(dim=1).values
        else:  # mean
            mask = attention_mask.unsqueeze(-1).float()
            summed = (last_hidden * mask).sum(dim=1)
            counts = mask.sum(dim=1).clamp(min=1.0)
            pooled = summed / counts
        return pooled


class CodeBERTClassifier(nn.Module):
    """CodeBERT encoder + MLP classifier head."""

    def __init__(self, cfg: CodeBERTConfig):
        super().__init__()
        self.cfg = cfg
        self.encoder = CodeBERTEncoder(cfg)

        # MLP head
        layers = []
        in_dim = cfg.hidden_size
        for h in cfg.classifier_hidden_dims:
            layers.append(nn.Linear(in_dim, h))
            layers.append(nn.GELU())
            layers.append(nn.Dropout(cfg.dropout))
            in_dim = h
        layers.append(nn.Linear(in_dim, cfg.n_classes))
        self.head = nn.Sequential(*layers)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> Dict[str, torch.Tensor]:
        pooled = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        logits = self.head(pooled)
        return {"logits": logits, "pooled": pooled}

    def embed(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Return only the pooled embedding (for FAISS / caching)."""
        return self.encoder(input_ids=input_ids, attention_mask=attention_mask)


# ----- Embedding cache ------------------------------------------------------

@torch.no_grad()
def compute_embeddings(
    model: CodeBERTEncoder,
    dataloader,
    device: torch.device,
    use_fp16: bool = False,
) -> Tuple[np.ndarray, list, list]:
    """Run the encoder over a dataloader and return mean-pooled embeddings.

    Returns (embeddings [N, H], sample_ids, projects).
    """
    model.eval()
    model.to(device)
    all_emb = []
    all_sids = []
    all_projs = []
    for batch in dataloader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        if use_fp16 and device.type == "cuda":
            with torch.amp.autocast("cuda"):
                emb = model(input_ids=input_ids, attention_mask=attention_mask)
        else:
            emb = model(input_ids=input_ids, attention_mask=attention_mask)
        all_emb.append(emb.cpu().float().numpy())
        all_sids.extend(batch["sample_ids"])
        all_projs.extend(batch["projects"])
    return np.concatenate(all_emb, axis=0), all_sids, all_projs


def save_embedding_cache(path: str, embeddings: np.ndarray, sample_ids: list, projects: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez_compressed(
        path,
        embeddings=embeddings,
        sample_ids=np.array(sample_ids, dtype=object),
        projects=np.array(projects, dtype=object),
    )
    print(f"[encoder] saved embedding cache -> {path}  shape={embeddings.shape}")


def load_embedding_cache(path: str) -> Tuple[np.ndarray, list, list]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Embedding cache not found: {path}")
    z = np.load(path, allow_pickle=True)
    return z["embeddings"], list(z["sample_ids"]), list(z["projects"])

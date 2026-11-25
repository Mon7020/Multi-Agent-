"""Shared runtime dependencies for RAG across API and services."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Dict


_rag_tool_instance = None


def get_rag_tool():
    """Return singleton RAG tool instance."""
    global _rag_tool_instance
    if _rag_tool_instance is None:
        from tools.rag_tool import rag_tool

        _rag_tool_instance = rag_tool
    return _rag_tool_instance


def get_loaded_rag_tool():
    """Return the loaded RAG tool instance without triggering initialization."""
    return _rag_tool_instance


class RAGParamsManager:
    """Versioned RAG settings shared by processes on the same filesystem."""

    _instance = None
    _params = {
        "chunk_size": 400,
        "chunk_overlap": 50,
        "top_k": None,  # populated from settings on first access
        "similarity_threshold": 0.3,
        "enable_cache": True,
        "enable_rerank": True,
        "enable_hybrid": True,
        "enable_self_rag": False,
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def _connect():
        path = Path(os.environ.get("RAG_PARAMS_DB") or Path(__file__).resolve().parents[3] / "data" / "settings" / "rag_params.sqlite3")
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(path), timeout=10)
        connection.execute("CREATE TABLE IF NOT EXISTS rag_params (id INTEGER PRIMARY KEY CHECK (id = 1), version INTEGER NOT NULL, params TEXT NOT NULL)")
        return connection

    def _defaults(self) -> Dict:
        from config.settings import settings
        params = self._params.copy()
        if params["top_k"] is None:
            params["top_k"] = settings.rag_top_k
        return params

    def get_params(self) -> Dict:
        with self._connect() as connection:
            row = connection.execute("SELECT params FROM rag_params WHERE id = 1").fetchone()
        params = self._defaults()
        if row:
            params.update(json.loads(row[0]))
        return params

    def get_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT version FROM rag_params WHERE id = 1").fetchone()
        return row[0] if row else 0

    def update_params(self, params: Dict):
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT version, params FROM rag_params WHERE id = 1").fetchone()
            merged = self._defaults()
            if row:
                merged.update(json.loads(row[1]))
            merged.update(params)
            connection.execute("INSERT OR REPLACE INTO rag_params (id, version, params) VALUES (1, ?, ?)",
                               ((row[0] if row else 0) + 1, json.dumps(merged)))

    def get_chunk_size(self) -> int:
        return self.get_params()["chunk_size"]

    def get_chunk_overlap(self) -> int:
        return self.get_params()["chunk_overlap"]

    def get_top_k(self) -> int:
        return self.get_params()["top_k"]

    def get_similarity_threshold(self) -> float:
        return self.get_params()["similarity_threshold"]

    def get_enable_cache(self) -> bool:
        return self.get_params()["enable_cache"]

    def get_enable_rerank(self) -> bool:
        return self.get_params()["enable_rerank"]

    def get_enable_self_rag(self) -> bool:
        return self.get_params()["enable_self_rag"]


rag_params_manager = RAGParamsManager()

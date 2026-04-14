"""Authentication service backed by a lightweight SQL database with signed tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
import urllib.parse
import uuid
from typing import Any, Dict, Optional, Tuple

import pymysql
from app.config import settings


class AuthError(Exception):
    """Auth domain error."""


class AuthService:
    def __init__(self, storage_path: Optional[str] = None, database_url: Optional[str] = None):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

        self._lock = threading.RLock()
        self.secret = os.getenv("APP_AUTH_SECRET", "change-this-auth-secret")
        self.default_token_ttl_seconds = 7 * 24 * 3600

        configured_url = database_url or os.getenv("DATABASE_URL") or settings.database_url
        self._db_type, self._db_config = self._resolve_database_url(configured_url, project_root)
        self._ensure_schema()

    @staticmethod
    def _resolve_database_url(url: str, project_root: str) -> Tuple[str, Dict[str, Any]]:
        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme
        if scheme in ("sqlite", "sqlite3"):
            raw_path = parsed.path or ":memory:"
            if raw_path.startswith("/") and not (len(raw_path) > 2 and raw_path[2] == ":"):
                raw_path = raw_path.lstrip("/")
            if raw_path in ("", ":memory:"):
                return "sqlite", {"path": ":memory:", "placeholder": "?"}
            if not os.path.isabs(raw_path):
                raw_path = os.path.join(project_root, raw_path)
            os.makedirs(os.path.dirname(raw_path), exist_ok=True)
            return "sqlite", {"path": raw_path, "placeholder": "?"}

        if scheme.startswith("mysql"):
            driver = "pymysql"
            if "+" in scheme:
                driver = scheme.split("+", 1)[1]
            username = urllib.parse.unquote(parsed.username or "")
            password = urllib.parse.unquote(parsed.password or "")
            host = parsed.hostname or "localhost"
            port = parsed.port or 3306
            database = parsed.path.lstrip("/") if parsed.path else ""
            query = urllib.parse.parse_qs(parsed.query)
            charset = query.get("charset", ["utf8mb4"])[0]
            return "mysql", {
                "driver": driver,
                "user": username,
                "password": password,
                "host": host,
                "port": port,
                "database": database,
                "charset": charset,
                "placeholder": "%s",
            }

        raise RuntimeError(f"Unsupported database URL: {url}")

    def _get_connection(self):
        if self._db_type == "sqlite":
            conn = sqlite3.connect(self._db_config["path"], check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn

        if self._db_type == "mysql":
            return pymysql.connect(
                host=self._db_config["host"],
                port=self._db_config["port"],
                user=self._db_config["user"],
                password=self._db_config["password"],
                database=self._db_config["database"],
                charset=self._db_config["charset"],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
            )

        raise RuntimeError("Unsupported database type")

    def _ensure_schema(self) -> None:
        conn = self._get_connection()
        try:
            sql = """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    status TEXT NOT NULL
                )
                """
            if self._db_type == "sqlite":
                conn.execute(sql)
            else:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _normalize_username(username: str) -> str:
        return (username or "").strip().lower()

    @staticmethod
    def _validate_username(username: str):
        if len(username) < 3 or len(username) > 64:
            raise AuthError("username length must be between 3 and 64")
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-@")
        if any(ch not in allowed for ch in username):
            raise AuthError("username contains unsupported characters")

    @staticmethod
    def _validate_password(password: str):
        if len(password) < 8:
            raise AuthError("password must be at least 8 characters")

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return dk.hex()

    @staticmethod
    def _b64url_encode(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    @staticmethod
    def _b64url_decode(raw: str) -> bytes:
        padding = "=" * ((4 - len(raw) % 4) % 4)
        return base64.urlsafe_b64decode((raw + padding).encode("utf-8"))

    def _fetch_user_by_username(self, conn, username: str) -> Optional[Dict[str, Any]]:
        placeholder = self._db_config.get("placeholder", "?")
        sql = f"""
            SELECT id, username, password_salt, password_hash, created_at, status
            FROM users
            WHERE username = {placeholder}
            LIMIT 1
            """
        if self._db_type == "sqlite":
            cursor = conn.execute(sql, (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

        with conn.cursor() as cursor:
            cursor.execute(sql, (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def _fetch_user_by_id(self, conn, user_id: str) -> Optional[Dict[str, Any]]:
        placeholder = self._db_config.get("placeholder", "?")
        sql = f"""
            SELECT id, username, created_at, status
            FROM users
            WHERE id = {placeholder}
            LIMIT 1
            """
        if self._db_type == "sqlite":
            cursor = conn.execute(sql, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def register(self, username: str, password: str) -> Dict[str, Any]:
        normalized = self._normalize_username(username)
        self._validate_username(normalized)
        self._validate_password(password)

        with self._lock:
            conn = self._get_connection()
            try:
                existing = self._fetch_user_by_username(conn, normalized)
                if existing:
                    raise AuthError("username already exists")

                user_id = f"usr_{uuid.uuid4().hex[:16]}"
                salt = secrets.token_hex(16)
                password_hash = self._hash_password(password, salt)
                created_at = int(time.time())
                placeholder = self._db_config.get("placeholder", "?")

                sql = f"""
                    INSERT INTO users (id, username, password_salt, password_hash, created_at, status)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                    """
                params = (user_id, normalized, salt, password_hash, created_at, "active")

                if self._db_type == "sqlite":
                    conn.execute(sql, params)
                else:
                    with conn.cursor() as cursor:
                        cursor.execute(sql, params)

                conn.commit()
            finally:
                conn.close()

        return {"id": user_id, "username": normalized, "created_at": created_at}

    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        normalized = self._normalize_username(username)
        with self._lock:
            conn = self._get_connection()
            try:
                user = self._fetch_user_by_username(conn, normalized)
            finally:
                conn.close()

        if not user:
            raise AuthError("invalid username or password")

        expected = user.get("password_hash", "")
        salt = user.get("password_salt", "")
        actual = self._hash_password(password, salt)
        if not hmac.compare_digest(expected, actual):
            raise AuthError("invalid username or password")

        if user.get("status") != "active":
            raise AuthError("user is disabled")

        return {"id": user["id"], "username": user["username"], "created_at": user.get("created_at")}

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not user_id:
            return None

        with self._lock:
            conn = self._get_connection()
            try:
                user = self._fetch_user_by_id(conn, user_id)
            finally:
                conn.close()

        if not user:
            return None

        return {
            "id": user["id"],
            "username": user["username"],
            "created_at": user.get("created_at"),
            "status": user.get("status"),
        }

    def create_token(self, user_id: str, username: str, ttl_seconds: Optional[int] = None) -> Dict[str, Any]:
        now = int(time.time())
        ttl = ttl_seconds or self.default_token_ttl_seconds
        exp = now + ttl

        payload = {
            "sub": user_id,
            "username": username,
            "iat": now,
            "exp": exp,
            "ver": 1,
        }
        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        payload_part = self._b64url_encode(payload_json)

        signature = hmac.new(self.secret.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
        token = f"{payload_part}.{self._b64url_encode(signature)}"

        return {"token": token, "expires_at": exp}

    def verify_token(self, token: str) -> Dict[str, Any]:
        if not token or "." not in token:
            raise AuthError("invalid token")

        try:
            payload_part, sig_part = token.split(".", 1)
        except ValueError as exc:
            raise AuthError("invalid token") from exc

        expected_sig = hmac.new(self.secret.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
        actual_sig = self._b64url_decode(sig_part)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise AuthError("invalid token signature")

        try:
            payload_raw = self._b64url_decode(payload_part)
            payload = json.loads(payload_raw.decode("utf-8"))
        except Exception as exc:
            raise AuthError("invalid token payload") from exc

        exp = int(payload.get("exp", 0))
        now = int(time.time())
        if exp <= now:
            raise AuthError("token expired")

        return payload

    def parse_bearer_token(self, authorization: Optional[str]) -> str:
        if not authorization:
            raise AuthError("authorization header missing")
        parts = authorization.strip().split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthError("authorization must use Bearer token")
        return parts[1].strip()

    def get_user_from_authorization(self, authorization: Optional[str]) -> Dict[str, Any]:
        token = self.parse_bearer_token(authorization)
        payload = self.verify_token(token)
        return {
            "id": payload.get("sub"),
            "username": payload.get("username"),
            "exp": payload.get("exp"),
            "token": token,
        }


auth_service = AuthService()

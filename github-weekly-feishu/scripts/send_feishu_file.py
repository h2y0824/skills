import json
import mimetypes
import os
import sys
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path


HOST = "https://open.larksuite.com"


def request_json(url, method="GET", token=None, payload=None, headers=None):
    final_headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        final_headers["Authorization"] = f"Bearer {token}"
    if headers:
        final_headers.update(headers)
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=final_headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_env(name):
    value = os.environ.get(name)
    if not value and os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value, _ = winreg.QueryValueEx(key, name)
        except OSError:
            value = None
    if not value:
        raise RuntimeError(f"missing environment variable: {name}")
    return value


def get_tenant_token():
    res = request_json(
        f"{HOST}/open-apis/auth/v3/tenant_access_token/internal",
        method="POST",
        payload={
            "app_id": get_env("FEISHU_APP_ID"),
            "app_secret": get_env("FEISHU_APP_SECRET"),
        },
    )
    if res.get("code", res.get("StatusCode")) != 0:
        raise RuntimeError(f"tenant token failed: {res}")
    return res["tenant_access_token"]


def multipart_body(fields, files):
    boundary = "----codex" + uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    for name, path in files.items():
        path = Path(path)
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode("utf-8")
        )
        chunks.append(f"Content-Type: {ctype}\r\n\r\n".encode())
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return boundary, b"".join(chunks)


def upload_file(token, file_path):
    file_path = Path(file_path)
    boundary, body = multipart_body(
        {"file_type": "stream", "file_name": file_path.name},
        {"file": file_path},
    )
    req = urllib.request.Request(
        f"{HOST}/open-apis/im/v1/files",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    if res.get("code", res.get("StatusCode")) != 0:
        raise RuntimeError(f"upload failed: {res}")
    return res["data"]["file_key"]


def send_file_by_webhook(file_key):
    webhook = get_env("FEISHU_WEBHOOK")
    return request_json(
        webhook,
        method="POST",
        payload={"msg_type": "file", "content": {"file_key": file_key}},
    )


def list_chats(token):
    chats = []
    page_token = ""
    while True:
        query = {"page_size": "100"}
        if page_token:
            query["page_token"] = page_token
        url = f"{HOST}/open-apis/im/v1/chats?{urllib.parse.urlencode(query)}"
        res = request_json(url, token=token)
        if res.get("code", res.get("StatusCode")) != 0:
            raise RuntimeError(f"list chats failed: {res}")
        data = res.get("data", {})
        chats.extend(data.get("items", []))
        page_token = data.get("page_token") or ""
        if not data.get("has_more"):
            break
    return chats


def send_file_to_chat(token, chat_id, file_key):
    content = json.dumps({"file_key": file_key}, ensure_ascii=False)
    url = f"{HOST}/open-apis/im/v1/messages?receive_id_type=chat_id"
    return request_json(
        url,
        method="POST",
        token=token,
        payload={"receive_id": chat_id, "msg_type": "file", "content": content},
    )


def main():
    if "--check-env" in sys.argv:
        for name in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_WEBHOOK", "FEISHU_CHAT_NAME"):
            try:
                get_env(name)
                status = "set"
            except RuntimeError:
                status = "missing"
            print(f"{name}={status}")
        return
    if len(sys.argv) != 2:
        raise SystemExit("usage: send_feishu_file.py <file-path>")

    file_path = Path(sys.argv[1]).resolve()
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    target_chat_name = get_env("FEISHU_CHAT_NAME")
    token = get_tenant_token()
    print("tenant_token_ok")
    file_key = upload_file(token, file_path)
    print("upload_ok")

    webhook_res = send_file_by_webhook(file_key)
    print("webhook_file_result", json.dumps(webhook_res, ensure_ascii=False))
    if webhook_res.get("code", webhook_res.get("StatusCode")) == 0:
        return

    chats = list_chats(token)
    matches = [c for c in chats if target_chat_name in (c.get("name") or "")]
    print(
        "chat_matches",
        json.dumps([{k: c.get(k) for k in ("chat_id", "name")} for c in matches], ensure_ascii=False),
    )
    if not matches:
        raise RuntimeError(f"no chat matched {target_chat_name!r}; add the app bot to the group and retry")
    send_res = send_file_to_chat(token, matches[0]["chat_id"], file_key)
    print("send_chat_result", json.dumps(send_res, ensure_ascii=False))
    if send_res.get("code", send_res.get("StatusCode")) != 0:
        raise RuntimeError(f"send file failed: {send_res}")
    time.sleep(0.2)


if __name__ == "__main__":
    main()

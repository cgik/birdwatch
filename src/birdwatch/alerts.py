import urllib.request


def send_ntfy(
    server: str,
    topic: str,
    message: str,
    *,
    title: str | None = None,
    priority: str = "default",
    timeout_s: float = 10,
    token: str | None = None,
) -> None:
    headers = {"Priority": priority}

    if title:
        headers["Title"] = title

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"{server.rstrip('/')}/{topic}",
        data=message.encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout_s):
        pass

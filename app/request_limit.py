"""ASGI request body bound that also covers streamed/chunked bodies."""


class RequestSizeLimitMiddleware:
    def __init__(self, app, max_bytes: int = 8192) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        size = 0
        too_large = False

        async def bounded_receive():
            nonlocal size, too_large
            if too_large:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > self.max_bytes:
                    too_large = True
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        async def track_send(message):
            if too_large:
                return
            await send(message)

        await self.app(scope, bounded_receive, track_send)
        if too_large:
            body = b"Request body too large"
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [
                        (b"content-type", b"text/plain; charset=utf-8"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})

from playwright.sync_api import Page, expect


def test_chat_page_load_and_send_flow(page: Page, live_server_url: str) -> None:
    page.route(
        "**/send-message-htmx",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="""
            <div class="message bot-message">
                <div class="message-content">
                    <p>Stubbed bot reply</p>
                    <div class="message-timestamp">10:00 AM</div>
                </div>
            </div>
            """,
        ),
    )

    page.goto(f"{live_server_url}/")

    expect(page.locator("#chat-form")).to_be_visible()
    expect(page.locator("#message-input")).to_be_visible()
    expect(page.locator("#chat-box")).to_contain_text("Ask the first question")

    page.fill("#message-input", "Hello from smoke test")
    page.click("#chat-form button[type='submit']")

    expect(page.locator("#chat-box .user-message p").last).to_have_text("Hello from smoke test")
    expect(page.locator("#chat-box .bot-message p").last).to_have_text("Stubbed bot reply")


def test_chat_disables_duplicate_submit_while_request_is_in_flight(page: Page, live_server_url: str) -> None:
    requests = []
    page.on(
        "request",
        lambda request: requests.append(request) if request.url.endswith("/send-message-htmx") else None,
    )
    page.route(
        "**/send-message-htmx",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="""
            <div class="message bot-message">
                <div class="message-content">
                    <div class="message-body">Delayed bot reply</div>
                    <div class="message-timestamp">10:00 AM</div>
                </div>
            </div>
            """,
        ),
    )
    page.add_init_script(
        """
        (() => {
            const originalOpen = XMLHttpRequest.prototype.open;
            const originalSend = XMLHttpRequest.prototype.send;

            XMLHttpRequest.prototype.open = function(method, url) {
                this.__chatUrl = url;
                return originalOpen.apply(this, arguments);
            };

            XMLHttpRequest.prototype.send = function(body) {
                if (this.__chatUrl && this.__chatUrl.includes('/send-message-htmx')) {
                    const xhr = this;
                    window.setTimeout(() => {
                        originalSend.call(xhr, body);
                    }, 500);
                    return;
                }

                return originalSend.apply(this, arguments);
            };
        })();
        """
    )

    page.goto(f"{live_server_url}/")

    page.fill("#message-input", "Only send once")
    page.click("#chat-form button[type='submit']")

    expect(page.locator("#send-button")).to_be_disabled()
    expect(page.locator("#message-input")).to_be_disabled()
    expect(page.locator("[data-typing-indicator='true']")).to_be_visible()
    expect(page.locator("#chat-request-status")).to_have_text("")

    page.locator("#chat-form").evaluate("(form) => form.requestSubmit()")

    expect(page.locator("#chat-box .user-message")).to_have_count(1)
    expect(page.locator("#chat-box .bot-message .message-body").last).to_have_text("Delayed bot reply")
    expect(page.locator("#send-button")).to_be_enabled()
    expect(page.locator("#message-input")).to_be_enabled()
    assert len(requests) == 1


def test_chat_reuses_chat_session_id_for_second_send_without_reload(page: Page, live_server_url: str) -> None:
    requests = []

    def handle_route(route):
        request = route.request
        requests.append(request.post_data or "")
        if len(requests) == 1:
            route.fulfill(
                status=200,
                content_type="text/html",
                body="""
                <div class="message bot-message">
                    <div class="message-content">
                        <div class="message-body">First reply</div>
                        <div class="message-timestamp">10:00 AM</div>
                    </div>
                </div>
                <input type="hidden" id="chat-session-id" name="chat_session_id" value="42" hx-swap-oob="true">
                """,
            )
            return

        route.fulfill(
            status=200,
            content_type="text/html",
            body="""
            <div class="message bot-message">
                <div class="message-content">
                    <div class="message-body">Second reply</div>
                    <div class="message-timestamp">10:01 AM</div>
                </div>
            </div>
            <input type="hidden" id="chat-session-id" name="chat_session_id" value="42" hx-swap-oob="true">
            """,
        )

    page.route("**/send-message-htmx", handle_route)
    page.goto(f"{live_server_url}/")

    page.fill("#message-input", "First message")
    page.click("#chat-form button[type='submit']")
    expect(page.locator("#chat-session-id")).to_have_value("42")

    page.fill("#message-input", "Second message")
    page.click("#chat-form button[type='submit']")

    expect(page.locator("#chat-session-id")).to_have_value("42")
    expect(page.locator("#chat-box .user-message")).to_have_count(2)
    expect(page.locator("#chat-box .bot-message .message-body").last).to_have_text("Second reply")
    assert len(requests) == 2
    assert "chat_session_id=42" in requests[1]


def test_chat_swaps_server_error_message_into_chat(page: Page, live_server_url: str) -> None:
    page.route(
        "**/send-message-htmx",
        lambda route: route.fulfill(
            status=503,
            content_type="text/html",
            body="""
            <div class="message bot-message error-message">
                <div class="message-content">
                    <div class="message-title">Service Unavailable</div>
                    <div class="message-body">The chat service is temporarily unavailable. Please try again shortly.</div>
                    <div class="message-timestamp">10:00 AM</div>
                </div>
            </div>
            """,
        ),
    )

    page.goto(f"{live_server_url}/")

    page.fill("#message-input", "Trigger an error")
    page.click("#chat-form button[type='submit']")

    expect(page.locator("#chat-box .error-message .message-title").last).to_have_text("Service Unavailable")
    expect(page.locator("#chat-box .error-message .message-body").last).to_have_text(
        "The chat service is temporarily unavailable. Please try again shortly."
    )
    expect(page.locator("#chat-request-status")).to_have_text(
        "The chat service is temporarily unavailable. Please try again shortly."
    )


def test_chat_renders_transport_failure_message_when_htmx_send_error_fires(
    page: Page,
    live_server_url: str,
) -> None:
    page.add_init_script(
        """
        (() => {
            const originalOpen = XMLHttpRequest.prototype.open;
            const originalSend = XMLHttpRequest.prototype.send;

            XMLHttpRequest.prototype.open = function(method, url) {
                this.__chatUrl = url;
                return originalOpen.apply(this, arguments);
            };

            XMLHttpRequest.prototype.send = function(body) {
                if (this.__chatUrl && this.__chatUrl.includes('/send-message-htmx')) {
                    return;
                }

                return originalSend.apply(this, arguments);
            };
        })();
        """
    )

    page.goto(f"{live_server_url}/")
    page.fill("#message-input", "Fail before response")
    page.click("#chat-form button[type='submit']")

    expect(page.locator("[data-typing-indicator='true']")).to_be_visible()
    expect(page.locator("#chat-request-status")).to_have_text("")

    page.evaluate(
        """
        (() => {
            const form = document.getElementById('chat-form');
            document.body.dispatchEvent(new CustomEvent('htmx:sendError', {
                bubbles: true,
                detail: {
                    requestConfig: { elt: form }
                }
            }));
        })();
        """
    )

    expect(page.locator("#chat-box .error-message .message-title").last).to_have_text("Service Unavailable")
    expect(page.locator("#chat-box .error-message .message-body").last).to_have_text(
        "Could not reach the chat service. Please try again shortly."
    )
    expect(page.locator("#chat-request-status")).to_have_text(
        "Could not reach the chat service. Please try again."
    )

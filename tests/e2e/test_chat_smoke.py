import re

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


def test_mobile_chat_drawer_switch_shows_loading_feedback(page: Page, live_server_url: str) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
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
                if (this.__chatUrl && this.__chatUrl.includes('/chats/1/transcript')) {
                    const xhr = this;
                    window.setTimeout(() => {
                        originalSend.call(xhr, body);
                    }, 250);
                    return;
                }

                return originalSend.apply(this, arguments);
            };
        })();
        """
    )
    page.route(
        "**/chats/1/transcript",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            headers={"HX-Push-Url": "/chats/1"},
            body="""
            <div class="message bot-message">
                <div class="message-content">
                    <div class="message-body">Loaded transcript</div>
                    <div class="message-timestamp">10:05 AM</div>
                </div>
            </div>
            <div id="chat-view-header" hx-swap-oob="true">
                <button type="button" class="chat-drawer-toggle" data-chat-drawer-toggle aria-controls="chat-list-panel" aria-expanded="false">Chats</button>
                <div>
                    <h2 class="chat-view-title">Chat 1</h2>
                </div>
                <div class="chat-view-meta">Mar 15, 10:05 AM</div>
            </div>
            <aside id="chat-list-panel" class="chat-sidebar" hx-swap-oob="true">
                <div class="chat-sidebar-header">
                    <div class="chat-sidebar-header-row">
                        <h2>Chats</h2>
                        <button type="button" class="chat-sidebar-close" data-chat-drawer-close aria-label="Close chat list">Close</button>
                    </div>
                    <a href="/chat-start" hx-get="/chat-start/transcript" hx-target="#chat-box" hx-swap="innerHTML" hx-push-url="true" class="chat-new-link" data-chat-nav="new">New chat</a>
                </div>
                <div class="chat-sidebar-body">
                    <a
                        href="/chats/1"
                        hx-get="/chats/1/transcript"
                        hx-target="#chat-box"
                        hx-swap="innerHTML"
                        hx-push-url="true"
                        class="chat-list-item is-active"
                        data-chat-id="1"
                        data-chat-nav="chat"
                        aria-current="page"
                    >Chat 1</a>
                </div>
            </aside>
            <input type="hidden" id="chat-session-id" name="chat_session_id" value="1" hx-swap-oob="true">
            """,
        ),
    )
    page.goto(f"{live_server_url}/")
    page.evaluate(
        """
        () => {
            const body = document.querySelector('.chat-sidebar-body');
            body.innerHTML = `
                <a
                    href="/chats/1"
                    hx-get="/chats/1/transcript"
                    hx-target="#chat-box"
                    hx-swap="innerHTML"
                    hx-push-url="true"
                    class="chat-list-item"
                    data-chat-id="1"
                    data-chat-nav="chat"
                >
                    <div class="chat-list-item-title">Chat 1</div>
                </a>
            `;
            window.htmx.process(body);
        }
        """
    )

    page.click("[data-chat-drawer-toggle]")
    expect(page.locator("#chat-list-panel")).to_have_class(re.compile(r".*\bis-open\b.*"))
    expect(page.locator("#chat-drawer-backdrop")).to_have_class(re.compile(r".*\bis-visible\b.*"))

    page.evaluate("document.querySelector(\"[data-chat-id='1']\").click()")

    expect(page.locator("#chat-navigation-status")).to_be_visible()
    expect(page.locator("#chat-navigation-status")).to_contain_text("Loading chat")
    expect(page.locator("#chat-box")).to_have_class(re.compile(r".*\bis-loading\b.*"))
    expect(page.locator("#chat-box .message-body").last).to_have_text("Loaded transcript")
    expect(page).to_have_url(f"{live_server_url}/chats/1")
    expect(page.locator("#chat-list-panel")).not_to_have_class(re.compile(r".*\bis-open\b.*"))
    expect(page.locator("#chat-navigation-status")).to_be_hidden()
    expect(page.locator("#chat-session-id")).to_have_value("1")


def test_new_chat_action_returns_to_start_screen_and_first_send_updates_url(
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
                if (this.__chatUrl && this.__chatUrl.includes('/chat-start/transcript')) {
                    const xhr = this;
                    window.setTimeout(() => {
                        originalSend.call(xhr, body);
                    }, 250);
                    return;
                }

                return originalSend.apply(this, arguments);
            };
        })();
        """
    )
    page.route(
        "**/chat-start/transcript",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            headers={"HX-Push-Url": "/chat-start"},
            body="""
            <div class="chat-empty-state" data-empty-state="true">
                <h3>Ask the first question</h3>
                <p>Your first message creates a saved transcript.</p>
            </div>
            <div id="chat-view-header" hx-swap-oob="true">
                <button type="button" class="chat-drawer-toggle" data-chat-drawer-toggle aria-controls="chat-list-panel" aria-expanded="false">Chats</button>
                <div>
                    <h2 class="chat-view-title">Start a new chat</h2>
                </div>
            </div>
            <aside id="chat-list-panel" class="chat-sidebar" hx-swap-oob="true">
                <div class="chat-sidebar-header">
                    <div class="chat-sidebar-header-row">
                        <h2>Chats</h2>
                        <button type="button" class="chat-sidebar-close" data-chat-drawer-close aria-label="Close chat list">Close</button>
                    </div>
                    <a href="/chat-start" hx-get="/chat-start/transcript" hx-target="#chat-box" hx-swap="innerHTML" hx-push-url="true" class="chat-new-link" data-chat-nav="new">New chat</a>
                </div>
                <div class="chat-sidebar-body">
                    <a
                        href="/chats/1"
                        hx-get="/chats/1/transcript"
                        hx-target="#chat-box"
                        hx-swap="innerHTML"
                        hx-push-url="true"
                        class="chat-list-item"
                        data-chat-id="1"
                        data-chat-nav="chat"
                    >Chat 1</a>
                </div>
            </aside>
            <input type="hidden" id="chat-session-id" name="chat_session_id" value="" hx-swap-oob="true">
            """,
        ),
    )
    page.route(
        "**/send-message-htmx",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            headers={"HX-Push-Url": "/chats/42"},
            body="""
            <div class="message bot-message">
                <div class="message-content">
                    <div class="message-body">Fresh reply</div>
                    <div class="message-timestamp">10:10 AM</div>
                </div>
            </div>
            <input type="hidden" id="chat-session-id" name="chat_session_id" value="42" hx-swap-oob="true">
            """,
        ),
    )
    page.goto(f"{live_server_url}/")
    page.evaluate(
        """
        () => {
            const body = document.querySelector('.chat-sidebar-body');
            body.innerHTML = `
                <a
                    href="/chats/1"
                    hx-get="/chats/1/transcript"
                    hx-target="#chat-box"
                    hx-swap="innerHTML"
                    hx-push-url="true"
                    class="chat-list-item is-active"
                    data-chat-id="1"
                    data-chat-nav="chat"
                    aria-current="page"
                >
                    <div class="chat-list-item-title">Chat 1</div>
                </a>
            `;
            window.htmx.process(body);
            const hiddenInput = document.getElementById('chat-session-id');
            hiddenInput.value = '1';
        }
        """
    )

    page.click(".chat-new-link")

    expect(page.locator("#chat-navigation-status")).to_be_visible()
    expect(page.locator("#chat-navigation-status")).to_contain_text("Starting a new chat")
    expect(page.locator("#chat-box")).to_contain_text("Ask the first question")
    expect(page).to_have_url(f"{live_server_url}/chat-start")
    expect(page.locator("#chat-session-id")).to_have_value("")

    page.fill("#message-input", "Start fresh")
    page.click("#chat-form button[type='submit']")

    expect(page.locator("#chat-box .user-message p").last).to_have_text("Start fresh")
    expect(page.locator("#chat-box .bot-message .message-body").last).to_have_text("Fresh reply")
    expect(page.locator("#chat-session-id")).to_have_value("42")
    expect(page).to_have_url(f"{live_server_url}/chats/42")

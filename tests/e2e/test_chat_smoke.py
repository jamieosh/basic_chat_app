import os
import re
from pathlib import Path
from textwrap import dedent
from urllib.parse import parse_qs

from playwright.sync_api import Page, expect

from persistence import ChatRepository
from utils.client_identity import CLIENT_ID_COOKIE_NAME


VISUAL_SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"


def _disable_motion(page: Page) -> None:
    page.add_style_tag(
        content="""
        *,
        *::before,
        *::after {
            animation: none !important;
            caret-color: transparent !important;
            transition: none !important;
        }
        """,
    )


def _assert_matches_visual_snapshot(page: Page, selector: str, snapshot_name: str) -> None:
    locator = page.locator(selector)
    actual_bytes = locator.screenshot(animations="disabled", caret="hide")
    snapshot_path = VISUAL_SNAPSHOT_DIR / snapshot_name

    if os.environ.get("UPDATE_VISUAL_BASELINES") == "1":
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_bytes(actual_bytes)
        return

    if not snapshot_path.exists():
        raise AssertionError(
            f"Missing visual snapshot {snapshot_path}. Run with UPDATE_VISUAL_BASELINES=1 to create it."
        )

    expected_bytes = snapshot_path.read_bytes()
    assert actual_bytes == expected_bytes, (
        f"Visual snapshot mismatch for {snapshot_name}. "
        "Run with UPDATE_VISUAL_BASELINES=1 to refresh it if the change is intentional."
    )


def _seed_visual_shell(
    page: Page,
    *,
    header_html: str,
    chat_box_html: str,
    sidebar_html: str,
    chat_session_id: str,
    drawer_open: bool = False,
) -> None:
    page.evaluate(
        """
        (state) => {
            document.getElementById('chat-view-header').innerHTML = state.headerHtml;
            document.getElementById('chat-box').innerHTML = state.chatBoxHtml;
            document.getElementById('chat-list-panel').innerHTML = state.sidebarHtml;
            document.getElementById('chat-session-id').value = state.chatSessionId;

            const panel = document.getElementById('chat-list-panel');
            panel.classList.toggle('is-open', state.drawerOpen);

            const backdrop = document.getElementById('chat-drawer-backdrop');
            backdrop.hidden = !state.drawerOpen;
            backdrop.classList.toggle('is-visible', state.drawerOpen);

            const toggle = document.querySelector('[data-chat-drawer-toggle]');
            if (toggle) {
                toggle.setAttribute('aria-expanded', state.drawerOpen ? 'true' : 'false');
            }
        }
        """,
        {
            "headerHtml": header_html,
            "chatBoxHtml": chat_box_html,
            "sidebarHtml": sidebar_html,
            "chatSessionId": chat_session_id,
            "drawerOpen": drawer_open,
        },
    )


def _active_chat_header_html() -> str:
    return dedent(
        """
        <button
            type="button"
            class="chat-drawer-toggle"
            data-chat-drawer-toggle
            aria-controls="chat-list-panel"
            aria-expanded="false"
            aria-label="Open chat list"
            title="Open chat list"
        >
            <span class="chat-drawer-toggle-icon" aria-hidden="true">
                <span></span>
                <span></span>
                <span></span>
            </span>
        </button>
        <div class="chat-view-body">
            <div class="chat-view-primary">
                <h2 class="chat-view-title">Chat 1</h2>
                <dl class="chat-session-meta" aria-label="Session metadata">
                    <div class="chat-session-meta-item">
                        <dt>Session</dt>
                        <dd>#1</dd>
                    </div>
                    <div class="chat-session-meta-item">
                        <dt>Created</dt>
                        <dd>Mar 14, 09:40 AM</dd>
                    </div>
                    <div class="chat-session-meta-item">
                        <dt>Updated</dt>
                        <dd>Mar 15, 11:12 AM</dd>
                    </div>
                    <div class="chat-session-meta-item">
                        <dt>Runtime</dt>
                        <dd>AI Chat</dd>
                    </div>
                    <div class="chat-session-meta-item">
                        <dt>Binding</dt>
                        <dd>openai</dd>
                    </div>
                    <div class="chat-session-meta-item">
                        <dt>Model</dt>
                        <dd>gpt-5-mini</dd>
                    </div>
                    <div class="chat-session-meta-item">
                        <dt>Provider</dt>
                        <dd>openai</dd>
                    </div>
                    <div class="chat-session-meta-item">
                        <dt>Run</dt>
                        <dd>#7 · chat_send · completed</dd>
                    </div>
                    <div class="chat-session-meta-item">
                        <dt>Run Updated</dt>
                        <dd>Mar 15, 11:12 AM</dd>
                    </div>
                </dl>
            </div>
            <div class="chat-view-actions">
                <div class="chat-view-meta">Mar 15, 11:12 AM</div>
                <button
                    type="button"
                    class="chat-delete-button"
                    data-chat-nav="delete"
                    aria-label="Delete chat"
                    title="Delete chat"
                >
                    <svg viewBox="0 0 24 24" class="chat-delete-icon" aria-hidden="true" focusable="false">
                        <path
                            d="M9 3h6l1 2h4v2H4V5h4l1-2zm1 6h2v8h-2V9zm4 0h2v8h-2V9zM7 9h2v8H7V9zm1 11a2 2 0 0 1-2-2V8h12v10a2 2 0 0 1-2 2H8z"
                            fill="currentColor"
                        />
                    </svg>
                </button>
            </div>
        </div>
        """
    ).strip()


def _start_header_html() -> str:
    return dedent(
        """
        <button
            type="button"
            class="chat-drawer-toggle"
            data-chat-drawer-toggle
            aria-controls="chat-list-panel"
            aria-expanded="false"
            aria-label="Open chat list"
            title="Open chat list"
        >
            <span class="chat-drawer-toggle-icon" aria-hidden="true">
                <span></span>
                <span></span>
                <span></span>
            </span>
        </button>
        <div>
            <h2 class="chat-view-title">Start a new chat</h2>
        </div>
        """
    ).strip()


def _sidebar_html() -> str:
    return dedent(
        """
        <div class="chat-sidebar-header border-b border-gray-200 p-4">
            <div class="chat-sidebar-header-row">
                <h2 class="text-sm font-bold text-gray-900 m-0">Chats</h2>
                <div class="chat-sidebar-header-actions">
                    <a
                        href="/chat-start"
                        hx-get="/chat-start/transcript"
                        hx-target="#chat-box"
                        hx-swap="innerHTML"
                        hx-push-url="true"
                        class="chat-new-link"
                        data-chat-nav="new"
                        aria-label="Start a new chat"
                        title="Start a new chat"
                    >
                        +
                    </a>
                    <button
                        type="button"
                        class="chat-sidebar-close"
                        data-chat-drawer-close
                        aria-label="Close chat list"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
        <div class="chat-sidebar-body flex flex-col gap-2 overflow-y-auto p-3 min-h-0">
            <a
                href="/chats/1"
                hx-get="/chats/1/transcript"
                hx-target="#chat-box"
                hx-swap="innerHTML"
                hx-push-url="true"
                class="chat-list-item block border border-gray-200 bg-white px-3 py-2 no-underline text-inherit is-active bg-gray-200 border-gray-400"
                data-chat-id="1"
                data-chat-nav="chat"
                aria-current="page"
            >
                <div class="flex items-center justify-between gap-3">
                    <div class="chat-list-item-title text-sm font-semibold text-gray-900 truncate">Chat 1</div>
                    <div class="chat-list-item-meta text-xs text-gray-500 whitespace-nowrap text-right">11:12 AM</div>
                </div>
            </a>
            <a
                href="/chats/2"
                hx-get="/chats/2/transcript"
                hx-target="#chat-box"
                hx-swap="innerHTML"
                hx-push-url="true"
                class="chat-list-item block border border-gray-200 bg-white px-3 py-2 no-underline text-inherit"
                data-chat-id="2"
                data-chat-nav="chat"
            >
                <div class="flex items-center justify-between gap-3">
                    <div class="chat-list-item-title text-sm font-semibold text-gray-900 truncate">Chat 2</div>
                    <div class="chat-list-item-meta text-xs text-gray-500 whitespace-nowrap text-right">Mar 14</div>
                </div>
            </a>
        </div>
        """
    ).strip()


def _active_chat_box_html() -> str:
    return dedent(
        """
        <div class="message user-message bg-primary-100 p-3 rounded-lg ml-auto max-w-[80%]">
            <div class="message-content">
                <p>Draft a launch plan for a new app.</p>
                <div class="message-timestamp">Mar 15, 11:11 AM</div>
            </div>
        </div>
        <div class="message bot-message">
            <div class="message-content">
                <div class="message-body">
                    Start with goals, audience, launch channels, and a one-week publishing plan.
                </div>
                <div class="message-timestamp">Mar 15, 11:12 AM</div>
            </div>
        </div>
        """
    ).strip()


def _seed_persisted_chat(db_path: Path, *, client_id: str) -> tuple[int, int]:
    repository = ChatRepository(db_path)
    older_chat = repository.create_chat(client_id=client_id, title="Chat 1")
    repository.create_message(
        chat_session_id=older_chat.id,
        client_id=client_id,
        role="user",
        content="Earlier message",
    )
    active_chat = repository.create_chat(client_id=client_id, title="Chat 2")
    repository.create_message(
        chat_session_id=active_chat.id,
        client_id=client_id,
        role="user",
        content="Persisted question",
    )
    repository.create_message(
        chat_session_id=active_chat.id,
        client_id=client_id,
        role="assistant",
        content="Persisted answer",
    )
    return older_chat.id, active_chat.id


def _assert_restored_chat_state(page: Page, *, active_chat_id: int) -> None:
    expect(page.locator("#chat-box")).to_contain_text("Persisted question")
    expect(page.locator("#chat-box")).to_contain_text("Persisted answer")
    expect(page.locator("#chat-session-id")).to_have_value(str(active_chat_id))
    expect(page.locator(f'[data-chat-id="{active_chat_id}"]')).to_have_attribute(
        "aria-current",
        "page",
    )


def _assert_follow_up_send_reuses_restored_chat_session(
    page: Page,
    *,
    active_chat_id: int,
    expected_message: str,
) -> None:
    requests: list[str] = []

    def handle_send(route) -> None:
        requests.append(route.request.post_data or "")
        route.fulfill(
            status=200,
            content_type="text/html",
            body=f"""
            <div class="message bot-message">
                <div class="message-content">
                    <div class="message-body">Follow-up reply</div>
                    <div class="message-timestamp">10:15 AM</div>
                </div>
            </div>
            <input
                type="hidden"
                id="chat-session-id"
                name="chat_session_id"
                value="{active_chat_id}"
                hx-swap-oob="true"
            >
            """,
        )

    page.route("**/send-message-htmx", handle_send)
    page.fill("#message-input", expected_message)
    page.click("#chat-form button[type='submit']")

    expect(page.locator("#chat-box")).to_contain_text(expected_message)
    expect(page.locator("#chat-box")).to_contain_text("Follow-up reply")
    assert len(requests) == 1
    payload = parse_qs(requests[0])
    assert payload["chat_session_id"][0] == str(active_chat_id)
    assert payload["request_id"][0] != ""


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


def test_chat_disables_duplicate_submit_while_request_is_in_flight(
    page: Page, live_server_url: str
) -> None:
    requests = []
    page.on(
        "request",
        lambda request: (
            requests.append(request) if request.url.endswith("/send-message-htmx") else None
        ),
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
    expect(page.locator("#chat-box .bot-message .message-body").last).to_have_text(
        "Delayed bot reply"
    )
    expect(page.locator("#send-button")).to_be_enabled()
    expect(page.locator("#message-input")).to_be_enabled()
    assert len(requests) == 1


def test_chat_reuses_chat_session_id_for_second_send_without_reload(
    page: Page, live_server_url: str
) -> None:
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
    initial_request_id = page.locator("#chat-request-id").input_value()
    assert initial_request_id != ""

    page.fill("#message-input", "First message")
    page.click("#chat-form button[type='submit']")
    expect(page.locator("#chat-session-id")).to_have_value("42")
    first_rotated_request_id = page.locator("#chat-request-id").input_value()
    assert first_rotated_request_id != ""
    assert first_rotated_request_id != initial_request_id

    page.fill("#message-input", "Second message")
    page.click("#chat-form button[type='submit']")

    expect(page.locator("#chat-session-id")).to_have_value("42")
    expect(page.locator("#chat-box .user-message")).to_have_count(2)
    expect(page.locator("#chat-box .bot-message .message-body").last).to_have_text("Second reply")
    assert len(requests) == 2
    assert "chat_session_id=42" in requests[1]
    first_payload = parse_qs(requests[0])
    second_payload = parse_qs(requests[1])
    assert first_payload["request_id"][0] == initial_request_id
    assert second_payload["request_id"][0] == first_rotated_request_id
    assert first_payload["request_id"][0] != second_payload["request_id"][0]


def test_chat_refresh_restores_existing_chat_transcript_and_follow_up_send(
    page: Page, live_server
) -> None:
    client_id = "refresh-client"
    _older_chat_id, active_chat_id = _seed_persisted_chat(
        live_server.database_path,
        client_id=client_id,
    )
    page.context.add_cookies(
        [
            {
                "name": CLIENT_ID_COOKIE_NAME,
                "value": client_id,
                "url": live_server.base_url,
            }
        ]
    )

    page.goto(f"{live_server.base_url}/chats/{active_chat_id}")
    _assert_restored_chat_state(page, active_chat_id=active_chat_id)

    page.reload()
    _assert_restored_chat_state(page, active_chat_id=active_chat_id)
    _assert_follow_up_send_reuses_restored_chat_session(
        page,
        active_chat_id=active_chat_id,
        expected_message="Follow-up after refresh",
    )


def test_chat_direct_revisit_restores_existing_chat_transcript_and_follow_up_send(
    page: Page, live_server
) -> None:
    client_id = "revisit-client"
    _older_chat_id, active_chat_id = _seed_persisted_chat(
        live_server.database_path,
        client_id=client_id,
    )
    page.context.add_cookies(
        [
            {
                "name": CLIENT_ID_COOKIE_NAME,
                "value": client_id,
                "url": live_server.base_url,
            }
        ]
    )

    revisit_page = page.context.new_page()
    revisit_page.goto(f"{live_server.base_url}/chats/{active_chat_id}")

    _assert_restored_chat_state(revisit_page, active_chat_id=active_chat_id)
    _assert_follow_up_send_reuses_restored_chat_session(
        revisit_page,
        active_chat_id=active_chat_id,
        expected_message="Follow-up after revisit",
    )


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

    expect(page.locator("#chat-box .error-message .message-title").last).to_have_text(
        "Service Unavailable"
    )
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

    expect(page.locator("#chat-box .error-message .message-title").last).to_have_text(
        "Service Unavailable"
    )
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


def test_delete_chat_confirmation_routes_to_remaining_chat(
    page: Page, live_server_url: str
) -> None:
    dialog_messages = []

    def accept_dialog(dialog) -> None:
        dialog_messages.append(dialog.message)
        dialog.accept()

    page.on("dialog", accept_dialog)
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
                if (this.__chatUrl && this.__chatUrl.includes('/chats/1/delete')) {
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
        "**/chats/1/delete",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            headers={"HX-Push-Url": "/chats/2"},
            body="""
            <div class="message bot-message">
                <div class="message-content">
                    <div class="message-body">Remaining transcript</div>
                    <div class="message-timestamp">10:12 AM</div>
                </div>
            </div>
            <div id="chat-view-header" hx-swap-oob="true">
                <button type="button" class="chat-drawer-toggle" data-chat-drawer-toggle aria-controls="chat-list-panel" aria-expanded="false">Chats</button>
                <div>
                    <h2 class="chat-view-title">Chat 2</h2>
                </div>
                <div class="flex items-center gap-3">
                    <div class="chat-view-meta">Mar 15, 10:12 AM</div>
                    <button
                        type="button"
                        hx-post="/chats/2/delete"
                        hx-target="#chat-box"
                        hx-swap="innerHTML"
                        hx-confirm="Delete this chat? This cannot be undone."
                        data-chat-nav="delete"
                    >Delete</button>
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
                        href="/chats/2"
                        hx-get="/chats/2/transcript"
                        hx-target="#chat-box"
                        hx-swap="innerHTML"
                        hx-push-url="true"
                        class="chat-list-item is-active"
                        data-chat-id="2"
                        data-chat-nav="chat"
                        aria-current="page"
                    >
                        <div class="chat-list-item-title">Chat 2</div>
                    </a>
                </div>
            </aside>
            <input type="hidden" id="chat-session-id" name="chat_session_id" value="2" hx-swap-oob="true">
            """,
        ),
    )

    page.goto(f"{live_server_url}/")
    page.evaluate(
        """
        () => {
            document.getElementById('chat-box').innerHTML = `
                <div class="message bot-message">
                    <div class="message-content">
                        <div class="message-body">Current transcript</div>
                        <div class="message-timestamp">10:10 AM</div>
                    </div>
                </div>
            `;
            document.getElementById('chat-view-header').innerHTML = `
                <button type="button" class="chat-drawer-toggle" data-chat-drawer-toggle aria-controls="chat-list-panel" aria-expanded="false">Chats</button>
                <div>
                    <h2 class="chat-view-title">Chat 1</h2>
                </div>
                <div class="flex items-center gap-3">
                    <div class="chat-view-meta">Mar 15, 10:10 AM</div>
                    <button
                        type="button"
                        hx-post="/chats/1/delete"
                        hx-target="#chat-box"
                        hx-swap="innerHTML"
                        hx-confirm="Delete this chat? This cannot be undone."
                        data-chat-nav="delete"
                    >Delete</button>
                </div>
            `;
            document.getElementById('chat-list-panel').innerHTML = `
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
                    >
                        <div class="chat-list-item-title">Chat 1</div>
                    </a>
                    <a
                        href="/chats/2"
                        hx-get="/chats/2/transcript"
                        hx-target="#chat-box"
                        hx-swap="innerHTML"
                        hx-push-url="true"
                        class="chat-list-item"
                        data-chat-id="2"
                        data-chat-nav="chat"
                    >
                        <div class="chat-list-item-title">Chat 2</div>
                    </a>
                </div>
            `;
            document.getElementById('chat-session-id').value = '1';
            window.htmx.process(document.getElementById('chat-view-header'));
            window.htmx.process(document.getElementById('chat-list-panel'));
        }
        """
    )

    page.click("button[data-chat-nav='delete']")

    expect(page.locator("#chat-navigation-status")).to_be_visible()
    expect(page.locator("#chat-navigation-status")).to_contain_text("Deleting chat")
    expect(page.locator("#chat-box .message-body").last).to_have_text("Remaining transcript")
    expect(page.locator("#chat-session-id")).to_have_value("2")
    expect(page.locator("#chat-view-header")).to_contain_text("Chat 2")
    expect(page.locator("#chat-list-panel")).not_to_contain_text("Chat 1")
    expect(page).to_have_url(f"{live_server_url}/chats/2")
    assert dialog_messages == ["Delete this chat? This cannot be undone."]


def test_delete_last_chat_confirmation_routes_to_start_screen(
    page: Page, live_server_url: str
) -> None:
    dialog_messages = []

    def accept_dialog(dialog) -> None:
        dialog_messages.append(dialog.message)
        dialog.accept()

    page.on("dialog", accept_dialog)
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
                if (this.__chatUrl && this.__chatUrl.includes('/chats/1/delete')) {
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
        "**/chats/1/delete",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            headers={"HX-Push-Url": "/chat-start"},
            body="""
            <div class="chat-empty-shell" data-empty-state="true">
                <div class="chat-empty-state">
                    <h3>Ask the first question</h3>
                    <p>Your first message creates a saved transcript.</p>
                </div>
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
                    <div class="chat-list-empty">No chats yet. Your first message will create one.</div>
                </div>
            </aside>
            <input type="hidden" id="chat-session-id" name="chat_session_id" value="" hx-swap-oob="true">
            """,
        ),
    )

    page.goto(f"{live_server_url}/")
    page.evaluate(
        """
        () => {
            document.getElementById('chat-box').innerHTML = `
                <div class="message bot-message">
                    <div class="message-content">
                        <div class="message-body">Only transcript</div>
                        <div class="message-timestamp">10:15 AM</div>
                    </div>
                </div>
            `;
            document.getElementById('chat-view-header').innerHTML = `
                <button type="button" class="chat-drawer-toggle" data-chat-drawer-toggle aria-controls="chat-list-panel" aria-expanded="false">Chats</button>
                <div>
                    <h2 class="chat-view-title">Chat 1</h2>
                </div>
                <div class="flex items-center gap-3">
                    <div class="chat-view-meta">Mar 15, 10:15 AM</div>
                    <button
                        type="button"
                        hx-post="/chats/1/delete"
                        hx-target="#chat-box"
                        hx-swap="innerHTML"
                        hx-confirm="Delete this chat? This cannot be undone."
                        data-chat-nav="delete"
                    >Delete</button>
                </div>
            `;
            document.getElementById('chat-list-panel').innerHTML = `
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
                    >
                        <div class="chat-list-item-title">Chat 1</div>
                    </a>
                </div>
            `;
            document.getElementById('chat-session-id').value = '1';
            window.htmx.process(document.getElementById('chat-view-header'));
            window.htmx.process(document.getElementById('chat-list-panel'));
        }
        """
    )

    page.click("button[data-chat-nav='delete']")

    expect(page.locator("#chat-navigation-status")).to_be_visible()
    expect(page.locator("#chat-navigation-status")).to_contain_text("Deleting chat")
    expect(page.locator("#chat-box")).to_contain_text("Ask the first question")
    expect(page.locator("#chat-view-header")).to_contain_text("Start a new chat")
    expect(page.locator("#chat-list-panel")).to_contain_text("No chats yet")
    expect(page.locator("#chat-session-id")).to_have_value("")
    expect(page).to_have_url(f"{live_server_url}/chat-start")
    assert dialog_messages == ["Delete this chat? This cannot be undone."]


def test_visual_desktop_start_screen(page: Page, live_server_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1024})
    page.goto(f"{live_server_url}/")
    _disable_motion(page)

    _assert_matches_visual_snapshot(page, ".chat-workspace", "chat-workspace-start-desktop.png")


def test_visual_desktop_active_chat_shell(page: Page, live_server_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1024})
    page.goto(f"{live_server_url}/")
    _disable_motion(page)
    _seed_visual_shell(
        page,
        header_html=_active_chat_header_html(),
        chat_box_html=_active_chat_box_html(),
        sidebar_html=_sidebar_html(),
        chat_session_id="1",
    )

    _assert_matches_visual_snapshot(page, ".chat-workspace", "chat-workspace-active-desktop.png")


def test_desktop_chat_headers_share_aligned_rails(page: Page, live_server_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1024})
    page.goto(f"{live_server_url}/")
    _disable_motion(page)
    _seed_visual_shell(
        page,
        header_html=_active_chat_header_html(),
        chat_box_html=_active_chat_box_html(),
        sidebar_html=_sidebar_html(),
        chat_session_id="1",
    )

    sidebar_box = page.locator(".chat-sidebar-header").bounding_box()
    header_box = page.locator("#chat-view-header").bounding_box()

    assert sidebar_box is not None
    assert header_box is not None
    assert abs(sidebar_box["y"] - header_box["y"]) <= 1
    assert header_box["height"] >= sidebar_box["height"]


def test_visual_mobile_active_chat_header(page: Page, live_server_url: str) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server_url}/")
    _disable_motion(page)
    _seed_visual_shell(
        page,
        header_html=_active_chat_header_html(),
        chat_box_html=_active_chat_box_html(),
        sidebar_html=_sidebar_html(),
        chat_session_id="1",
    )

    _assert_matches_visual_snapshot(page, "#chat-view-header", "chat-header-active-mobile.png")


def test_visual_mobile_drawer_open(page: Page, live_server_url: str) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server_url}/")
    _disable_motion(page)
    _seed_visual_shell(
        page,
        header_html=_start_header_html(),
        chat_box_html="""
        <div class="chat-empty-shell" data-empty-state="true">
            <div class="chat-empty-state rounded-lg border border-dashed border-slate-300 bg-slate-50 px-5 py-5 max-w-2xl">
                <h3 class="text-base font-bold text-slate-900 m-0">Ask the first question</h3>
                <p class="text-sm leading-6 text-slate-600 mt-2 mb-0">Conversations in this browser are saved automatically and can be reopened from their URL.</p>
            </div>
        </div>
        """.strip(),
        sidebar_html=_sidebar_html(),
        chat_session_id="",
        drawer_open=True,
    )

    _assert_matches_visual_snapshot(page, ".bg-white.shadow-lg", "chat-drawer-open-mobile.png")

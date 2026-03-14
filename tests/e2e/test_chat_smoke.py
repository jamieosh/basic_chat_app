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
    expect(page.locator("#chat-box .bot-message").first).to_contain_text(
        "Hello! How can I help you today?"
    )

    page.fill("#message-input", "Hello from smoke test")
    page.click("#chat-form button[type='submit']")

    expect(page.locator("#chat-box .user-message p").last).to_have_text("Hello from smoke test")
    expect(page.locator("#chat-box .bot-message p").last).to_have_text("Stubbed bot reply")

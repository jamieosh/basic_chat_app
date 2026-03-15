class ChatUI {
    constructor(options = {}) {
        this.endpoint = options.endpoint || '/send-message-htmx';
        this.chatBoxId = options.chatBoxId || 'chat-box';
        this.formId = options.formId || 'chat-form';
        this.messageInputId = options.messageInputId || 'message-input';
        this.submitButtonId = options.submitButtonId || 'send-button';
        this.requestStatusId = options.requestStatusId || 'chat-request-status';
        this.navigationStatusId = options.navigationStatusId || 'chat-navigation-status';
        this.requestInFlight = false;
        this.transportErrorHandled = false;
        this.navigationRequestInFlight = false;

        this.init();
    }

    init() {
        this.form = document.getElementById(this.formId);
        this.chatBox = document.getElementById(this.chatBoxId);
        this.messageInput = document.getElementById(this.messageInputId);
        this.submitButton = document.getElementById(this.submitButtonId);
        this.requestStatus = document.getElementById(this.requestStatusId);
        this.navigationStatus = document.getElementById(this.navigationStatusId);
        this.chatAvailable = this.form ? this.form.dataset.chatAvailable !== 'false' : false;
        this.serviceUnavailableMessage = this.form?.dataset.serviceUnavailableMessage
            || 'The chat service is temporarily unavailable. Please try again shortly.';

        // Initialize textarea auto-resize
        this.initTextarea();

        this.syncDrawerState(false);

        // Add event listeners
        this.addEventListeners();

        this.setControlsDisabled(!this.chatAvailable);
        if (!this.chatAvailable) {
            this.setRequestStatus(this.serviceUnavailableMessage, 'error');
        }

        // Initial scroll to bottom
        this.scrollToBottom();
    }

    initTextarea() {
        const textarea = this.messageInput;
        if (!textarea) return;

        // Set initial height
        this.adjustTextareaHeight(textarea);
        this.syncSubmitButtonHeight(textarea);

        // Add input event listener for auto-resize
        textarea.addEventListener('input', () => {
            this.adjustTextareaHeight(textarea);
            this.syncSubmitButtonHeight(textarea);
        });

        // Handle Enter key (Shift+Enter for new line)
        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (this.form && textarea.value.trim() && !this.requestInFlight && this.chatAvailable) {
                    if (typeof this.form.requestSubmit === 'function') {
                        this.form.requestSubmit();
                    } else {
                        this.form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                    }
                }
            }
        });
    }

    adjustTextareaHeight(textarea) {
        // Reset height to auto to get the correct scrollHeight
        textarea.style.height = 'auto';

        // Calculate if content exceeds max height
        const maxHeight = 240;
        const shouldScroll = textarea.scrollHeight > maxHeight;

        // Set new height based on scrollHeight, with a maximum
        textarea.style.height = Math.min(textarea.scrollHeight, maxHeight) + 'px';

        // Add or remove scrolling class based on content height
        textarea.classList.toggle('scrolling', shouldScroll);
    }

    resetTextarea() {
        const textarea = this.messageInput;
        if (textarea) {
            textarea.value = '';
            textarea.style.height = 'auto';
            this.adjustTextareaHeight(textarea);
            this.syncSubmitButtonHeight(textarea);
        }
    }

    syncSubmitButtonHeight(textarea) {
        const submitButton = this.submitButton;
        if (!submitButton) return;

        submitButton.style.height = `${textarea.offsetHeight}px`;
    }

    getFormattedTime() {
        const now = new Date();
        let hours = now.getHours();
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';

        hours = hours % 12;
        hours = hours ? hours : 12; // Convert 0 to 12
        const formattedHours = hours.toString().padStart(2, '0');

        return `${formattedHours}:${minutes} ${ampm}`;
    }

    scrollToBottom() {
        const chatBox = this.chatBox;
        if (chatBox) {
            // Use a small timeout to ensure the DOM has updated
            setTimeout(() => {
                chatBox.scrollTop = chatBox.scrollHeight;
            }, 100);
        }
    }

    createTypingIndicator() {
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'message bot-message fade-in';
        typingIndicator.dataset.typingIndicator = 'true';
        typingIndicator.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator-row">
                    <div class="typing-indicator-dots" aria-hidden="true">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        `;
        return typingIndicator;
    }

    addEventListeners() {
        if (this.form) {
            this.form.addEventListener('submit', (event) => {
                this.handleSubmit(event);
            });

            this.form.addEventListener('htmx:beforeRequest', (event) => {
                this.handleBeforeRequest(event);
            });
        }

        if (document.body) {
            document.body.addEventListener('click', (event) => {
                this.handleBodyClick(event);
            });

            document.body.addEventListener('keydown', (event) => {
                this.handleBodyKeydown(event);
            });

            document.body.addEventListener('htmx:beforeSwap', (event) => {
                this.handleBeforeSwap(event);
            });

            document.body.addEventListener('htmx:afterRequest', (event) => {
                this.handleAfterRequest(event);
            });

            document.body.addEventListener('htmx:beforeRequest', (event) => {
                this.handleNavigationBeforeRequest(event);
            });

            document.body.addEventListener('htmx:sendError', (event) => {
                this.handleTransportError(event);
            });

            document.body.addEventListener('htmx:timeout', (event) => {
                this.handleTransportError(event);
            });

            document.body.addEventListener('htmx:sendAbort', (event) => {
                this.handleTransportError(event);
            });

            document.body.addEventListener('htmx:afterSwap', (event) => {
                this.handleAfterSwap(event);
                this.scrollToBottom();
            });
        }

        window.addEventListener('resize', () => {
            if (!this.isMobileViewport()) {
                this.closeDrawer();
            }
        });
    }

    handleBodyClick(event) {
        const toggle = event.target.closest('[data-chat-drawer-toggle]');
        if (toggle) {
            if (this.isDrawerOpen()) {
                this.closeDrawer();
            } else {
                this.openDrawer();
            }
            return;
        }

        if (event.target.closest('[data-chat-drawer-close]') || event.target.closest('[data-chat-drawer-backdrop]')) {
            this.closeDrawer();
        }
    }

    handleBodyKeydown(event) {
        if (event.key === 'Escape' && this.isDrawerOpen()) {
            this.closeDrawer();
        }
    }

    getChatListPanel() {
        return document.getElementById('chat-list-panel');
    }

    getDrawerBackdrop() {
        return document.querySelector('[data-chat-drawer-backdrop]');
    }

    getDrawerToggle() {
        return document.querySelector('[data-chat-drawer-toggle]');
    }

    isMobileViewport() {
        return window.matchMedia('(max-width: 768px)').matches;
    }

    isDrawerOpen() {
        const panel = this.getChatListPanel();
        return Boolean(panel && panel.classList.contains('is-open'));
    }

    syncDrawerState(isOpen) {
        const toggle = this.getDrawerToggle();
        if (toggle) {
            toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        }
    }

    openDrawer() {
        if (!this.isMobileViewport()) return;

        const panel = this.getChatListPanel();
        const backdrop = this.getDrawerBackdrop();
        if (!panel || !backdrop) return;

        panel.classList.add('is-open');
        backdrop.hidden = false;
        requestAnimationFrame(() => {
            backdrop.classList.add('is-visible');
        });
        this.syncDrawerState(true);
    }

    closeDrawer() {
        const panel = this.getChatListPanel();
        const backdrop = this.getDrawerBackdrop();

        if (panel) {
            panel.classList.remove('is-open');
        }

        if (backdrop) {
            backdrop.classList.remove('is-visible');
            window.setTimeout(() => {
                if (!backdrop.classList.contains('is-visible')) {
                    backdrop.hidden = true;
                }
            }, 200);
        }

        this.syncDrawerState(false);
    }

    handleSubmit(event) {
        if (!this.form || event.target !== this.form) return;

        if (!this.chatAvailable || this.requestInFlight) {
            event.preventDefault();
            return;
        }

        const message = this.messageInput?.value.trim() || '';
        if (!message) {
            event.preventDefault();
            this.setRequestStatus('Enter a message before sending.', 'error');
        }
    }

    handleBeforeRequest(event) {
        if (event.target !== this.form) return;

        const message = this.messageInput?.value.trim() || '';
        if (!message) {
            event.preventDefault();
            this.finishRequest({ preserveStatus: false });
            return;
        }

        if (this.requestInFlight) {
            event.preventDefault();
            return;
        }

        this.requestInFlight = true;
        this.transportErrorHandled = false;
        this.setControlsDisabled(true);
        this.setRequestStatus('', 'idle');

        // Add user message
        this.addUserMessage(message);

        // Add typing indicator
        this.addTypingIndicator();
    }

    addUserMessage(message) {
        const chatBox = this.chatBox;
        if (!chatBox) return;

        this.clearEmptyState();

        const currentTime = this.getFormattedTime();
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'message user-message bg-primary-100 p-3 rounded-lg ml-auto max-w-[80%] fade-in';

        const messageContentDiv = document.createElement('div');
        messageContentDiv.className = 'message-content';

        const messageParagraph = document.createElement('p');
        messageParagraph.textContent = message;

        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        timestampDiv.textContent = currentTime;

        messageContentDiv.appendChild(messageParagraph);
        messageContentDiv.appendChild(timestampDiv);
        userMessageDiv.appendChild(messageContentDiv);

        chatBox.appendChild(userMessageDiv);
    }

    addBotMessage(title, body, isError = false) {
        const chatBox = this.chatBox;
        if (!chatBox) return;

        const currentTime = this.getFormattedTime();
        const botMessageDiv = document.createElement('div');
        botMessageDiv.className = `message bot-message fade-in${isError ? ' error-message' : ''}`;

        const messageContentDiv = document.createElement('div');
        messageContentDiv.className = 'message-content';

        if (title) {
            const titleDiv = document.createElement('div');
            titleDiv.className = 'message-title';
            titleDiv.textContent = title;
            messageContentDiv.appendChild(titleDiv);
        }

        const bodyDiv = document.createElement('div');
        bodyDiv.className = 'message-body';
        bodyDiv.textContent = body;

        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        timestampDiv.textContent = currentTime;

        messageContentDiv.appendChild(bodyDiv);
        messageContentDiv.appendChild(timestampDiv);
        botMessageDiv.appendChild(messageContentDiv);
        chatBox.appendChild(botMessageDiv);
    }

    clearEmptyState() {
        const chatBox = this.chatBox;
        if (!chatBox) return;

        chatBox.querySelectorAll('[data-empty-state="true"]').forEach((element) => {
            element.remove();
        });
    }

    addTypingIndicator() {
        const chatBox = this.chatBox;
        if (!chatBox) return;

        const typingIndicator = this.createTypingIndicator();
        chatBox.appendChild(typingIndicator);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const indicator = this.chatBox?.querySelector('[data-typing-indicator="true"]');
        if (indicator) {
            indicator.remove();
        }
    }

    handleBeforeSwap(event) {
        if (this.isTrackedRequestEvent(event)) {
            this.removeTypingIndicator();

            const status = event.detail.xhr?.status || 0;
            if (status >= 400) {
                event.detail.shouldSwap = true;
                event.detail.isError = false;
                this.setRequestStatus(this.statusMessageForStatus(status), 'error');
            }
            return;
        }

        if (this.isNavigationRequestEvent(event)) {
            const status = event.detail.xhr?.status || 0;
            if (status >= 400) {
                event.detail.shouldSwap = true;
                event.detail.isError = false;
            }
        }
    }

    handleAfterRequest(event) {
        if (this.isTrackedRequestEvent(event)) {
            const status = event.detail.xhr?.status || 0;
            const failed = status >= 400 || Boolean(event.detail.failed);

            if (status === 0 && failed && !this.transportErrorHandled) {
                this.handleTransportError(event);
                return;
            }

            this.finishRequest({ preserveStatus: failed });
            return;
        }

        if (this.isNavigationRequestEvent(event)) {
            this.finishNavigationRequest();
        }
    }

    handleNavigationBeforeRequest(event) {
        const trigger = this.navigationTriggerFromEvent(event);
        if (!trigger) return;

        this.navigationRequestInFlight = true;
        this.setPendingNavigation(trigger);
        this.setNavigationLoading(true, this.navigationLabelForTrigger(trigger));
        this.closeDrawer();
    }

    handleAfterSwap(event) {
        if (!this.isNavigationRequestEvent(event)) return;

        this.closeDrawer();
        this.syncDrawerState(false);
    }

    finishNavigationRequest() {
        this.navigationRequestInFlight = false;
        this.clearPendingNavigation();
        this.setNavigationLoading(false);
    }

    setNavigationLoading(isLoading, message = 'Loading chat...') {
        if (this.navigationStatus) {
            this.navigationStatus.hidden = !isLoading;
            const statusText = this.navigationStatus.querySelector('.chat-navigation-status-text');
            if (statusText) {
                statusText.textContent = message;
            }
        }

        if (this.chatBox) {
            this.chatBox.classList.toggle('is-loading', isLoading);
        }
    }

    setPendingNavigation(trigger) {
        this.clearPendingNavigation();
        trigger.classList.add('is-pending');
    }

    clearPendingNavigation() {
        document.querySelectorAll('[data-chat-nav].is-pending').forEach((element) => {
            element.classList.remove('is-pending');
        });
    }

    navigationLabelForTrigger(trigger) {
        if (trigger.dataset.chatNav === 'new') {
            return 'Starting a new chat...';
        }

        return 'Loading chat...';
    }

    navigationTriggerFromEvent(event) {
        const requestElt = event.detail?.requestConfig?.elt;
        if (!requestElt || typeof requestElt.closest !== 'function') {
            return null;
        }

        return requestElt.closest('[data-chat-nav]');
    }

    isNavigationRequestEvent(event) {
        return Boolean(this.navigationTriggerFromEvent(event));
    }

    handleTransportError(event) {
        if (this.isTrackedRequestEvent(event)) {
            if (!this.requestInFlight) return;
            if (this.transportErrorHandled) return;

            this.transportErrorHandled = true;
            this.removeTypingIndicator();
            this.addBotMessage(
                'Service Unavailable',
                'Could not reach the chat service. Please try again shortly.',
                true,
            );
            this.finishRequest({ preserveStatus: true });
            this.setRequestStatus('Could not reach the chat service. Please try again.', 'error');
            return;
        }

        if (this.isNavigationRequestEvent(event)) {
            this.finishNavigationRequest();
        }
    }

    finishRequest({ preserveStatus }) {
        this.requestInFlight = false;
        this.transportErrorHandled = false;
        this.resetTextarea();
        this.setControlsDisabled(false);

        if (!preserveStatus) {
            this.setRequestStatus('', 'idle');
        }
    }

    setControlsDisabled(disabled) {
        const shouldDisable = disabled || !this.chatAvailable;

        if (this.messageInput) {
            this.messageInput.disabled = shouldDisable;
            this.messageInput.setAttribute('aria-disabled', shouldDisable ? 'true' : 'false');
        }

        if (this.submitButton) {
            this.submitButton.disabled = shouldDisable;
            this.submitButton.setAttribute('aria-disabled', shouldDisable ? 'true' : 'false');
        }
    }

    setRequestStatus(message, state) {
        if (!this.requestStatus) return;

        this.requestStatus.textContent = message;
        if (state && state !== 'idle') {
            this.requestStatus.dataset.state = state;
            return;
        }

        delete this.requestStatus.dataset.state;
    }

    statusMessageForStatus(status) {
        if (status === 400) {
            return 'Message rejected. Update it and try again.';
        }

        if (status === 401) {
            return 'The chat service authentication failed.';
        }

        if (status === 429) {
            return 'The chat service is busy. Please try again shortly.';
        }

        if (status === 503 || status === 504) {
            return this.serviceUnavailableMessage;
        }

        return 'The chat request failed. Please try again.';
    }

    isTrackedRequestEvent(event) {
        if (!this.form) return false;

        if (event.target === this.form) {
            return true;
        }

        const requestElt = event.detail?.requestConfig?.elt;
        if (requestElt) {
            return requestElt === this.form;
        }

        return this.requestInFlight;
    }
}

// Initialize chat when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatUI = new ChatUI();
    
    // Handle viewport height issues on mobile
    function setMobileHeight() {
        document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`);
    }
    
    // Set initial height and update on resize
    setMobileHeight();
    window.addEventListener('resize', setMobileHeight);
}); 

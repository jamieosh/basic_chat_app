class ChatUI {
    constructor(options = {}) {
        this.endpoint = options.endpoint || '/send-message-htmx';
        this.chatBoxId = options.chatBoxId || 'chat-box';
        this.formId = options.formId || 'chat-form';
        this.messageInputId = options.messageInputId || 'message-input';
        this.welcomeTimestampId = options.welcomeTimestampId || 'welcome-timestamp';
        
        this.init();
    }
    
    init() {
        // Set welcome message timestamp
        const welcomeTimestamp = document.getElementById(this.welcomeTimestampId);
        if (welcomeTimestamp) {
            welcomeTimestamp.textContent = this.getFormattedTime();
        }
        
        // Initialize textarea auto-resize
        this.initTextarea();
        
        // Add event listeners
        this.addEventListeners();
        
        // Initial scroll to bottom
        this.scrollToBottom();
    }
    
    initTextarea() {
        const textarea = document.getElementById(this.messageInputId);
        if (!textarea) return;

        // Set initial height
        this.adjustTextareaHeight(textarea);

        // Add input event listener for auto-resize
        textarea.addEventListener('input', () => {
            this.adjustTextareaHeight(textarea);
        });

        // Handle Enter key (Shift+Enter for new line)
        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const form = document.getElementById(this.formId);
                if (form && textarea.value.trim()) {
                    form.dispatchEvent(new Event('submit'));
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
        const textarea = document.getElementById(this.messageInputId);
        if (textarea) {
            textarea.value = '';
            textarea.style.height = 'auto';
            this.adjustTextareaHeight(textarea);
        }
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
        const chatBox = document.getElementById(this.chatBoxId);
        if (chatBox) {
            // Use a small timeout to ensure the DOM has updated
            setTimeout(() => {
                chatBox.scrollTop = chatBox.scrollHeight;
            }, 100);
        }
    }
    
    createTypingIndicator() {
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'message bot-message bg-gray-100 p-3 rounded-lg max-w-[90%] sm:max-w-[80%] fade-in';
        typingIndicator.innerHTML = `
            <div class="flex items-center h-6">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        return typingIndicator;
    }
    
    addEventListeners() {
        // Form submission
        const form = document.getElementById(this.formId);
        if (form) {
            form.addEventListener('htmx:beforeRequest', (event) => {
                this.handleBeforeRequest(event);
            });
        }
        
        // Response handling
        document.body.addEventListener('htmx:beforeSwap', () => {
            this.removeTypingIndicator();
        });
        
        // After request cleanup
        document.body.addEventListener('htmx:afterRequest', () => {
            this.handleAfterRequest();
        });
        
        // After content added
        document.body.addEventListener('htmx:afterSwap', () => {
            this.scrollToBottom();
        });
    }
    
    handleBeforeRequest(event) {
        const messageInput = document.getElementById(this.messageInputId);
        if (!messageInput) return;
        
        const message = messageInput.value.trim();
        
        if (!message) {
            event.preventDefault();
            return;
        }
        
        // Add user message
        this.addUserMessage(message);
        
        // Add typing indicator
        this.addTypingIndicator();
        
        // Add timestamp to form
        this.addTimestampToForm(event.target);
    }
    
    addUserMessage(message) {
        const chatBox = document.getElementById(this.chatBoxId);
        if (!chatBox) return;
        
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
    
    addTypingIndicator() {
        const chatBox = document.getElementById(this.chatBoxId);
        if (!chatBox) return;
        
        const typingIndicator = this.createTypingIndicator();
        chatBox.appendChild(typingIndicator);
        this.scrollToBottom();
    }
    
    removeTypingIndicator() {
        const typingIndicators = document.querySelectorAll('.typing-dot');
        if (typingIndicators.length > 0) {
            const indicator = typingIndicators[0].closest('.message');
            if (indicator) {
                indicator.remove();
            }
        }
    }
    
    addTimestampToForm(form) {
        if (!form) return;
        
        const timeInput = document.createElement('input');
        timeInput.type = 'hidden';
        timeInput.name = 'timestamp';
        timeInput.value = this.getFormattedTime();
        form.appendChild(timeInput);
    }
    
    handleAfterRequest() {
        this.resetTextarea();
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

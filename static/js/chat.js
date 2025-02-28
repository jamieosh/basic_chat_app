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
        
        // Add event listeners
        this.addEventListeners();
        
        // Initial scroll to bottom
        this.scrollToBottom();
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
            chatBox.scrollTop = chatBox.scrollHeight;
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
        userMessageDiv.innerHTML = `
            <div class="message-content">
                <p>${message}</p>
                <div class="message-timestamp">${currentTime}</div>
            </div>
        `;
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
        const messageInput = document.getElementById(this.messageInputId);
        if (messageInput) {
            messageInput.value = '';
            messageInput.focus();
        }
        
        // Remove timestamp inputs
        const timeInputs = document.querySelectorAll('input[name="timestamp"]');
        timeInputs.forEach(input => input.remove());
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
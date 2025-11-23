/**
 * Content script for voice-controlled browser extension.
 * Executes actions and shows real-time status overlay.
 */

console.log('Voice browser content script loaded');

// Create status widget
const widget = document.createElement('div');
widget.id = 'voice-browser-widget';
widget.innerHTML = `
    <div id="voice-status" class="status-idle">
        <div class="status-indicator"></div>
        <div class="status-text">Ready</div>
    </div>
    <div id="voice-transcription" class="transcription-hidden"></div>
`;

const styles = document.createElement('style');
styles.textContent = `
    #voice-browser-widget {
        position: fixed;
        top: 16px;
        right: 16px;
        z-index: 2147483647;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        pointer-events: none;
    }
    
    #voice-status {
        display: flex;
        align-items: center;
        gap: 8px;
        background: rgba(0, 0, 0, 0.85);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 8px 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .status-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        transition: all 0.3s ease;
    }
    
    .status-idle .status-indicator {
        background: #10b981;
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
    }
    
    .status-listening .status-indicator {
        background: #3b82f6;
        animation: pulse 1.5s ease-in-out infinite;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.8);
    }
    
    .status-listening .status-text::after {
        content: '';
        animation: dots 1.5s steps(4, end) infinite;
    }
    
    @keyframes dots {
        0%, 20% { content: ''; }
        40% { content: '.'; }
        60% { content: '..'; }
        80%, 100% { content: '...'; }
    }
    
    .status-processing .status-indicator {
        background: #f59e0b;
        animation: spin 1s linear infinite;
        box-shadow: 0 0 8px rgba(245, 158, 11, 0.5);
    }
    
    .status-error .status-indicator {
        background: #ef4444;
        box-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
    }
    
    .status-text {
        color: white;
        font-size: 13px;
        font-weight: 500;
        white-space: nowrap;
    }
    
    #voice-transcription {
        margin-top: 8px;
        background: rgba(0, 0, 0, 0.9);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 12px 16px;
        color: #e5e7eb;
        font-size: 14px;
        line-height: 1.4;
        max-width: 300px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .transcription-hidden {
        opacity: 0;
        transform: translateY(-10px);
        max-height: 0;
        overflow: hidden;
    }
    
    .transcription-visible {
        opacity: 1;
        transform: translateY(0);
        max-height: 200px;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.2); }
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;

// Inject widget on load - force immediate injection
function injectWidget() {
    if (!document.getElementById('voice-browser-widget')) {
        console.log('💉 Injecting voice browser widget...');
        if (!document.head.contains(styles)) {
            document.head.appendChild(styles);
        }
        if (document.body) {
            document.body.appendChild(widget);
            console.log('✅ Widget injected successfully');
        } else {
            console.log('⏳ Body not ready, waiting...');
            setTimeout(injectWidget, 50);
        }
    }
}

// Try immediate injection
injectWidget();

// Also inject on DOMContentLoaded as fallback
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectWidget);
}

// Update widget status
function updateStatus(status, text) {
    console.log('🔄 updateStatus called:', status, text);
    const statusDiv = document.getElementById('voice-status');
    const statusText = statusDiv?.querySelector('.status-text');
    
    if (statusDiv && statusText) {
        console.log('✅ Updating widget:', status, text);
        statusDiv.className = `status-${status}`;
        statusText.textContent = text;
    } else {
        console.error('❌ Widget elements not found:', {statusDiv, statusText});
    }
}

// Update transcription display
function updateTranscription(text, isPartial = false) {
    const transcriptionDiv = document.getElementById('voice-transcription');
    
    if (transcriptionDiv && text) {
        // Add "Transcribing:" prefix for partial results
        const displayText = isPartial ? `Transcribing: ${text}` : text;
        transcriptionDiv.textContent = displayText;
        transcriptionDiv.className = 'transcription-visible';
        
        // Auto-hide complete transcriptions after 3 seconds
        if (!isPartial) {
            setTimeout(() => {
                transcriptionDiv.className = 'transcription-hidden';
            }, 3000);
        }
    } else if (transcriptionDiv) {
        transcriptionDiv.className = 'transcription-hidden';
    }
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('✅ Content script received:', message);
    
    const action = message.action;
    
    // Handle status updates
    if (message.type === 'status') {
        console.log('📊 Updating status:', action.status, action.text);
        updateStatus(action.status, action.text);
        sendResponse({ success: true });
        return true;
    }
    
    // Handle transcription updates
    if (message.type === 'transcription') {
        console.log('📝 Updating transcription:', action.text, 'partial:', action.partial);
        updateTranscription(action.text, action.partial);
        sendResponse({ success: true });
        return true;
    }
    
    if (!action) {
        console.error('No action specified');
        sendResponse({ success: false, error: 'No action' });
        return true;
    }
    
    // Show processing status for actions
    updateStatus('processing', 'Executing...');
    
    try {
        switch (action.type) {
            case 'scroll':
                handleScroll(action);
                sendResponse({ success: true });
                break;
                
            case 'click':
                handleClick(action);
                sendResponse({ success: true });
                break;
                
            case 'input':
                handleInput(action);
                sendResponse({ success: true });
                break;
                
            case 'navigate':
                handleNavigate(action);
                sendResponse({ success: true });
                break;
                
            case 'tab':
                handleTab(action);
                sendResponse({ success: true });
                break;
                
            case 'browser':
                handleBrowser(action);
                sendResponse({ success: true });
                break;
                
            default:
                console.error('Unknown action type:', action.type);
                updateStatus('error', 'Unknown action');
                setTimeout(() => updateStatus('idle', 'Ready'), 2000);
                sendResponse({ success: false, error: 'Unknown action' });
        }
        
        // Reset to ready state after action completes
        setTimeout(() => updateStatus('idle', 'Ready'), 1500);
        
    } catch (error) {
        console.error('Action error:', error);
        updateStatus('error', 'Action failed');
        setTimeout(() => updateStatus('idle', 'Ready'), 2000);
        sendResponse({ success: false, error: error.message });
    }
    
    return true;
});

// Action handlers
function handleScroll(action) {
    const direction = action.direction || 'down';
    const amount = action.amount || window.innerHeight * 0.8;
    
    if (direction === 'up') {
        window.scrollBy({ top: -amount, behavior: 'smooth' });
    } else if (direction === 'down') {
        window.scrollBy({ top: amount, behavior: 'smooth' });
    } else if (direction === 'top') {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (direction === 'bottom') {
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    }
}

function handleClick(action) {
    const text = action.text;
    const selector = action.selector;
    
    let element = null;
    
    if (selector) {
        element = document.querySelector(selector);
    } else if (text) {
        // Find element by text content
        const elements = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"]'));
        element = elements.find(el => 
            el.textContent.toLowerCase().includes(text.toLowerCase()) ||
            el.value?.toLowerCase().includes(text.toLowerCase()) ||
            el.getAttribute('aria-label')?.toLowerCase().includes(text.toLowerCase())
        );
    }
    
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => element.click(), 300);
    } else {
        console.warn('Element not found:', text || selector);
    }
}

function handleInput(action) {
    const value = action.value;
    const activeElement = document.activeElement;
    
    if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
        activeElement.value = value;
        activeElement.dispatchEvent(new Event('input', { bubbles: true }));
        activeElement.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
        // Try to find a visible input field
        const inputs = document.querySelectorAll('input[type="text"], input[type="search"], textarea');
        const visibleInput = Array.from(inputs).find(input => {
            const rect = input.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        });
        
        if (visibleInput) {
            visibleInput.focus();
            visibleInput.value = value;
            visibleInput.dispatchEvent(new Event('input', { bubbles: true }));
            visibleInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }
}

function handleNavigate(action) {
    const url = action.url;
    if (url) {
        window.location.href = url;
    }
}

function handleTab(action) {
    // Tab control is handled by background script
    console.log('Tab action:', action.action);
    // Forward to background script
    chrome.runtime.sendMessage({ action: action }, (response) => {
        if (chrome.runtime.lastError) {
            console.error('Failed to send tab action to background:', chrome.runtime.lastError);
        }
    });
}

function handleBrowser(action) {
    switch (action.action) {
        case 'back':
            window.history.back();
            break;
        case 'forward':
            window.history.forward();
            break;
        case 'refresh':
            window.location.reload();
            break;
        case 'stop':
            window.stop();
            break;
    }
}

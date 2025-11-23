/**
 * Background service worker for voice browser extension.
 * Receives commands from Python backend and forwards to content scripts.
 */

console.log('Voice browser background script loaded');

let ws = null;
let reconnectInterval = null;

// Inject content script into all existing tabs on extension load
async function injectContentScriptIntoAllTabs() {
    const tabs = await chrome.tabs.query({});
    console.log(`📋 Injecting content script into ${tabs.length} existing tabs...`);
    
    for (const tab of tabs) {
        // Skip chrome:// and other restricted URLs
        if (tab.url && !tab.url.startsWith('chrome://') && !tab.url.startsWith('chrome-extension://')) {
            try {
                await chrome.scripting.executeScript({
                    target: { tabId: tab.id },
                    files: ['content.js']
                });
                console.log(`✅ Injected into tab ${tab.id}`);
            } catch (error) {
                console.debug(`Cannot inject into tab ${tab.id}:`, error.message);
            }
        }
    }
}

// Inject on extension startup
injectContentScriptIntoAllTabs();

// Connect to Python backend WebSocket
function connectWebSocket() {
    try {
        ws = new WebSocket('ws://localhost:8080/ws');
        
        ws.onopen = () => {
            console.log('Connected to voice browser backend');
            if (reconnectInterval) {
                clearInterval(reconnectInterval);
                reconnectInterval = null;
            }
            
            // Notify all tabs that we're connected
            broadcastToAllTabs({ 
                type: 'status', 
                action: { status: 'idle', text: 'Ready' } 
            });
        };
        
        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log('✅ Received from backend:', message);
                
                // Broadcast to ALL tabs, not just active
                chrome.tabs.query({}, (tabs) => {
                    tabs.forEach(tab => {
                        chrome.tabs.sendMessage(tab.id, message, (response) => {
                            if (chrome.runtime.lastError) {
                                // Ignore errors for tabs without content script
                                console.debug('Tab', tab.id, 'not ready:', chrome.runtime.lastError.message);
                            } else {
                                console.log('✅ Message sent to tab', tab.id);
                            }
                        });
                    });
                });
            } catch (error) {
                console.error('Error processing message:', error);
            }
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        ws.onclose = () => {
            console.log('Disconnected from voice browser backend');
            ws = null;
            
            // Try to reconnect every 5 seconds
            if (!reconnectInterval) {
                reconnectInterval = setInterval(connectWebSocket, 5000);
            }
        };
        
    } catch (error) {
        console.error('Failed to connect:', error);
        if (!reconnectInterval) {
            reconnectInterval = setInterval(connectWebSocket, 5000);
        }
    }
}

// Broadcast message to all tabs
function broadcastToAllTabs(message) {
    chrome.tabs.query({}, (tabs) => {
        tabs.forEach(tab => {
            chrome.tabs.sendMessage(tab.id, message).catch(() => {
                // Ignore errors for tabs without content script
            });
        });
    });
}

// Start connection
connectWebSocket();

// Handle tab actions that need background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    const action = message.action;
    
    if (action?.type === 'tab') {
        handleTabAction(action);
        sendResponse({ success: true });
    }
    
    return true;
});

function handleTabAction(action) {
    switch (action.action) {
        case 'new':
            chrome.tabs.create({});
            break;
        case 'close':
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                if (tabs[0]) {
                    chrome.tabs.remove(tabs[0].id);
                }
            });
            break;
        case 'next':
            chrome.tabs.query({ currentWindow: true }, (tabs) => {
                chrome.tabs.query({ active: true, currentWindow: true }, (activeTabs) => {
                    const activeIndex = tabs.findIndex(t => t.id === activeTabs[0].id);
                    const nextIndex = (activeIndex + 1) % tabs.length;
                    chrome.tabs.update(tabs[nextIndex].id, { active: true });
                });
            });
            break;
        case 'previous':
            chrome.tabs.query({ currentWindow: true }, (tabs) => {
                chrome.tabs.query({ active: true, currentWindow: true }, (activeTabs) => {
                    const activeIndex = tabs.findIndex(t => t.id === activeTabs[0].id);
                    const prevIndex = (activeIndex - 1 + tabs.length) % tabs.length;
                    chrome.tabs.update(tabs[prevIndex].id, { active: true });
                });
            });
            break;
        case 'switch':
            if (action.index !== undefined) {
                chrome.tabs.query({ currentWindow: true }, (tabs) => {
                    if (tabs[action.index]) {
                        chrome.tabs.update(tabs[action.index].id, { active: true });
                    }
                });
            }
            break;
    }
}

/**
 * AI Voice Agent Platform - Embeddable Call Button
 * 
 * This script creates a floating call button on external websites.
 * When clicked, it opens a popup with a WebRTC call interface.
 * 
 * Usage:
 * <script 
 *   src="https://your-platform.com/embed/call-button.js"
 *   data-agent-id="your-agent-id"
 *   data-api-url="https://api.your-platform.com"
 *   data-button-text="Call Us"
 *   data-button-color="#3b82f6"
 *   data-button-text-color="#ffffff"
 *   data-button-border-radius="8"
 *   data-button-size="medium"
 *   data-button-position="bottom-right"
 *   data-button-style="filled"
 * ></script>
 */

(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    baseUrl: '',
    popupWidth: 400,
    popupHeight: 600,
  };

  function findEmbedScript() {
    const scripts = document.getElementsByTagName('script');
    for (let i = 0; i < scripts.length; i++) {
      if (scripts[i].src && scripts[i].src.includes('/embed/call-button.js')) {
        return scripts[i];
      }
    }
    return null;
  }

  function trimTrailingSlashes(value) {
    return String(value || '').replace(/\/+$/, '');
  }

  // Detect base URL from script src
  function detectBaseUrl() {
    const script = findEmbedScript();
    if (script && script.src) {
      return script.src.replace('/embed/call-button.js', '');
    }
    // Fallback to current origin
    return window.location.origin;
  }

  CONFIG.baseUrl = detectBaseUrl();

  // Parse configuration from data attributes
  function getConfig() {
    const currentScript = findEmbedScript();

    if (!currentScript) {
      console.error('[AI Call Button] Script not found');
      return null;
    }

    const dataset = currentScript.dataset;
    
    return {
      agentId: dataset.agentId,
      // The API may be served from a different origin than the static script,
      // especially in local and split frontend/backend deployments.
      apiUrl: trimTrailingSlashes(dataset.apiUrl || CONFIG.baseUrl),
      buttonText: dataset.buttonText || 'Call Us',
      buttonColor: dataset.buttonColor || '#3b82f6',
      buttonTextColor: dataset.buttonTextColor || '#ffffff',
      buttonBorderRadius: parseInt(dataset.buttonBorderRadius) || 8,
      buttonSize: dataset.buttonSize || 'medium',
      buttonPosition: dataset.buttonPosition || 'bottom-right',
      buttonStyle: dataset.buttonStyle || 'filled',
    };
  }

  // Create and inject styles
  function injectStyles() {
    const styles = document.createElement('style');
    styles.textContent = `
      .ai-call-button-wrapper {
        position: fixed;
        z-index: 999999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
      }
      
      .ai-call-button {
        border: none;
        cursor: pointer;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
      }
      
      .ai-call-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
      }
      
      .ai-call-button:active {
        transform: translateY(0);
      }
      
      .ai-call-button-icon {
        width: 20px;
        height: 20px;
      }
      
      .ai-call-popup-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 999999;
        display: none;
        align-items: center;
        justify-content: center;
      }
      
      .ai-call-popup-overlay.active {
        display: flex;
      }
      
      .ai-call-popup {
        background: white;
        border-radius: 12px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        width: 90%;
        max-width: 400px;
        height: 80%;
        max-height: 600px;
        overflow: hidden;
        position: relative;
      }
      
      .ai-call-popup iframe {
        width: 100%;
        height: 100%;
        border: none;
      }
      
      .ai-call-popup-close {
        position: absolute;
        top: 12px;
        right: 12px;
        width: 32px;
        height: 32px;
        border: none;
        background: rgba(0, 0, 0, 0.5);
        color: white;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        transition: background 0.2s;
        z-index: 10;
      }
      
      .ai-call-popup-close:hover {
        background: rgba(0, 0, 0, 0.7);
      }
      
      @media (max-width: 480px) {
        .ai-call-popup {
          width: 100%;
          height: 100%;
          max-width: none;
          max-height: none;
          border-radius: 0;
        }
      }
    `;
    document.head.appendChild(styles);
  }

  // Create phone icon SVG
  function createPhoneIcon(color) {
    return `
      <svg class="ai-call-button-icon" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
      </svg>
    `;
  }

  // Get position styles
  function getPositionStyles(position) {
    const positions = {
      'bottom-right': { bottom: '20px', right: '20px' },
      'bottom-left': { bottom: '20px', left: '20px' },
      'bottom-center': { bottom: '20px', left: '50%', transform: 'translateX(-50%)' },
      'top-right': { top: '20px', right: '20px' },
      'top-left': { top: '20px', left: '20px' },
      'top-center': { top: '20px', left: '50%', transform: 'translateX(-50%)' },
      'center': { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' },
    };
    return positions[position] || positions['bottom-right'];
  }

  // Get size styles
  function getSizeStyles(size) {
    const sizes = {
      'small': { padding: '8px 16px', fontSize: '14px' },
      'medium': { padding: '12px 24px', fontSize: '16px' },
      'large': { padding: '16px 32px', fontSize: '18px' },
    };
    return sizes[size] || sizes['medium'];
  }

  // Create the call button
  function createButton(config) {
    const wrapper = document.createElement('div');
    wrapper.className = 'ai-call-button-wrapper';
    
    const positionStyles = getPositionStyles(config.buttonPosition);
    Object.assign(wrapper.style, positionStyles);

    const button = document.createElement('button');
    button.className = 'ai-call-button';
    button.innerHTML = `
      ${createPhoneIcon(config.buttonTextColor)}
      <span>${config.buttonText}</span>
    `;
    
    const sizeStyles = getSizeStyles(config.buttonSize);
    const isOutline = config.buttonStyle === 'outline';
    button.style.cssText = `
      background-color: ${isOutline ? '#ffffff' : config.buttonColor};
      color: ${config.buttonTextColor};
      border-radius: ${config.buttonBorderRadius}px;
      padding: ${sizeStyles.padding};
      font-size: ${sizeStyles.fontSize};
      ${isOutline ? `border: 2px solid ${config.buttonColor};` : 'border: none;'}
    `;

    button.addEventListener('click', () => {
      if (!button.disabled) {
        void openPopup(config, button);
      }
    });

    wrapper.appendChild(button);
    document.body.appendChild(wrapper);
  }

  function platformOrigin() {
    return new URL(CONFIG.baseUrl, window.location.href).origin;
  }

  function sourcePageUrl() {
    try {
      const url = new URL(window.location.href);
      url.username = '';
      url.password = '';
      url.search = '';
      url.hash = '';
      return url.toString();
    } catch {
      return window.location.origin + window.location.pathname;
    }
  }

  async function requestEmbedToken(config) {
    const sourceUrl = encodeURIComponent(sourcePageUrl());
    const apiUrl = trimTrailingSlashes(config.apiUrl || CONFIG.baseUrl);
    const response = await fetch(
      `${apiUrl}/api/v1/embed/agent/${encodeURIComponent(config.agentId)}/token?source_url=${sourceUrl}`,
      {
        method: 'POST',
        credentials: 'omit',
      }
    );
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = body && body.detail;
      const message =
        detail && typeof detail === 'object' && detail.message
          ? detail.message
          : typeof detail === 'string'
            ? detail
            : 'This call button is not authorized on the current website.';
      throw new Error(message);
    }
    return body;
  }

  function showEmbedError(message) {
    const error = document.createElement('div');
    error.setAttribute('role', 'alert');
    error.textContent = message;
    error.style.cssText = [
      'position: fixed',
      'left: 20px',
      'bottom: 20px',
      'z-index: 1000000',
      'max-width: 320px',
      'padding: 12px 16px',
      'border-radius: 8px',
      'background: #7f1d1d',
      'color: #ffffff',
      'font: 14px/1.4 -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif',
      'box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2)',
    ].join(';');
    document.body.appendChild(error);
    setTimeout(() => error.remove(), 5000);
  }

  // Create and open popup after the host-page request has been authorized.
  async function openPopup(config, button) {
    const originalButtonText = button.querySelector('span');
    const originalLabel = originalButtonText ? originalButtonText.textContent : null;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    if (originalButtonText) originalButtonText.textContent = 'Starting…';

    let credentials;
    try {
      credentials = await requestEmbedToken(config);
    } catch (error) {
      console.error('[AI Call Button] Could not start call:', error);
      showEmbedError(error instanceof Error ? error.message : 'Could not start the call.');
      button.disabled = false;
      button.removeAttribute('aria-busy');
      if (originalButtonText) originalButtonText.textContent = originalLabel || config.buttonText;
      return;
    }

    // Remove existing popup if any
    const existingOverlay = document.querySelector('.ai-call-popup-overlay');
    if (existingOverlay) {
      closePopup();
    }

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'ai-call-popup-overlay';
    
    // Create popup
    const popup = document.createElement('div');
    popup.className = 'ai-call-popup';
    
    // Create iframe
    const iframe = document.createElement('iframe');
    iframe.src = `${CONFIG.baseUrl}/embed/call?agentId=${encodeURIComponent(config.agentId)}`;
    iframe.allow = 'microphone; camera';
    const sendCredentials = () => {
      iframe.contentWindow?.postMessage(
        {
          type: 'AI_CALL_INIT',
          token: credentials.token,
          wsUrl: credentials.wsUrl,
          sessionId: credentials.sessionId,
          demoCallsRemaining: credentials.demo_calls_remaining,
          demoMaxCallDurationSeconds: credentials.demo_max_call_duration_seconds,
        },
        platformOrigin()
      );
    };
    iframe.addEventListener('load', sendCredentials, { once: true });

    // Listen before inserting the iframe so the ready handshake cannot race
    // hydration inside the embedded page.
    const handleMessage = (event) => {
      if (
        event.source !== iframe.contentWindow ||
        event.origin !== platformOrigin() ||
        !event.data
      ) {
        return;
      }
      if (event.data.type === 'AI_CALL_READY') {
        sendCredentials();
      } else if (event.data.type === 'AI_CALL_CLOSE') {
        closePopup();
      }
    };
    window.addEventListener('message', handleMessage);
    overlay._messageHandler = handleMessage;

    popup.appendChild(iframe);
    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // Show popup
    setTimeout(() => {
      overlay.classList.add('active');
    }, 10);

    // Note: Removed overlay click-to-close to prevent accidental call termination
    // The call can only be ended by clicking the hang-up button inside the iframe

    // Close on Escape key (only when not in active call)
    document.addEventListener('keydown', handleEscape);

    button.disabled = false;
    button.removeAttribute('aria-busy');
    if (originalButtonText) originalButtonText.textContent = originalLabel || config.buttonText;
  }

  // Close popup
  function closePopup() {
    const overlay = document.querySelector('.ai-call-popup-overlay');
    if (overlay) {
      // Clean up message listener
      if (overlay._messageHandler) {
        window.removeEventListener('message', overlay._messageHandler);
      }
      overlay.classList.remove('active');
      setTimeout(() => {
        overlay.remove();
      }, 300);
    }
    document.removeEventListener('keydown', handleEscape);
  }

  // Handle Escape key
  function handleEscape(e) {
    if (e.key === 'Escape') {
      closePopup();
    }
  }

  // Initialize
  function init() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
      return;
    }

    // Get configuration
    const config = getConfig();
    if (!config || !config.agentId) {
      console.error('[AI Call Button] Missing agent-id configuration');
      return;
    }

    // Inject styles
    injectStyles();

    // Create button
    createButton(config);

    console.log('[AI Call Button] Initialized for agent:', config.agentId);
  }

  // Start initialization
  init();
})();

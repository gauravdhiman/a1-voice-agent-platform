# Embed Call Button Feature

## Overview

The Embed Call Button feature allows users to add a customizable voice call button to any external website. Visitors can click the button to start a real-time voice conversation with an AI agent through WebRTC, without leaving the website.

## Key Features

- **Customizable Appearance**: Button text, colors, size, position, and style
- **One-Click Embed**: Copy-paste ready embed code
- **Secure Access**: Time-limited tokens with domain validation
- **Rate Limiting**: Configurable daily call limits
- **Real-Time Calls**: WebRTC-based voice conversations

## Getting Started

### 1. Configure the Embed Button

Navigate to your agent's detail page and click the "Embed Button" button to open the configuration panel.

### 2. Customize Appearance

Configure the following settings:

| Setting | Description | Default |
|---------|-------------|---------|
| Button Text | Text displayed on the button | "Call Us" |
| Primary Color | Button background/border color | #3b82f6 |
| Text Color | Button text color | #ffffff |
| Border Radius | Corner roundness (0-50px) | 8 |
| Button Size | small, medium, or large | medium |
| Position | Location on the page | bottom-right |
| Button Style | filled or outline | filled |

### 3. Set Security Options

- **Allowed Domains**: Restrict which domains can use the embed (optional)
- **Daily Call Limit**: Maximum calls per day from this embed (default: 100)
- **Enable/Disable**: Toggle the embed on/off

### 4. Copy the Embed Code

After saving, copy the generated embed code and paste it into your website's HTML, just before the closing `</body>` tag.

## Embed Code Structure

```html
<!-- AI Voice Agent Call Button -->
<script
  src="https://your-platform.com/embed/call-button.js"
  data-agent-id="your-agent-id"
  data-button-text="Call Us"
  data-button-color="#3b82f6"
  data-button-text-color="#ffffff"
  data-button-border-radius="8"
  data-button-size="medium"
  data-button-position="bottom-right"
  data-button-style="filled"
></script>
```

## User Flow

```mermaid
sequenceDiagram
    participant Visitor as Website Visitor
    participant Website as External Website
    participant Script as Embed Script
    participant Platform as Platform API
    participant LiveKit as LiveKit

    Visitor->>Website: Load page with embed
    Website->>Script: Load call-button.js
    Script->>Website: Display floating button
    
    Visitor->>Script: Click button
    Script->>Script: Open modal with iframe
    Script->>Platform: Request embed token
    Platform->>Platform: Validate domain & rate limits
    Platform-->>Script: Return LiveKit token
    Script->>LiveKit: Connect with token
    LiveKit-->>Visitor: Start voice call
```

## Security

### Token-Based Access

- Tokens are generated on-demand when a visitor clicks the button
- Tokens expire after 1 hour
- Each token is scoped to a specific agent and room

### Domain Validation

When allowed domains are configured:
- Requests from unauthorized domains are rejected
- Both `Origin` and `Referer` headers are checked
- Subdomains of allowed domains are permitted

### Rate Limiting

- Daily call limits prevent abuse
- Limits are tracked per embed configuration
- When exceeded, visitors see a friendly error message

## API Endpoints

### Public Endpoints (No Authentication)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/embed/agent/{id}/info` | GET | Get public agent info |
| `/api/v1/embed/agent/{id}/token` | POST | Generate embed token |

### Authenticated Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents/{id}/embed-config` | GET | Get embed configuration |
| `/api/v1/agents/{id}/embed-config` | POST | Create/update configuration |
| `/api/v1/agents/{id}/embed-config` | DELETE | Delete configuration |

## Configuration Reference

### EmbedConfigCreate

```typescript
interface EmbedConfigCreate {
  buttonText: string;           // Button label
  buttonColor: string;          // Hex color (e.g., "#3b82f6")
  buttonTextColor: string;      // Hex color for text
  buttonBorderRadius: number;   // 0-50 pixels
  buttonSize: 'small' | 'medium' | 'large';
  buttonPosition: 'bottom-right' | 'bottom-left' | 'bottom-center' | 
                  'top-right' | 'top-left' | 'top-center' | 'center';
  buttonStyle?: 'filled' | 'outline';
  allowedDomains?: string[];    // Optional domain restrictions
  customCss?: string;           // Optional custom CSS
  isActive: boolean;            // Enable/disable
  dailyCallLimit: number;       // Max calls per day
}
```

## Updating Embed Code

When you update your embed configuration:

1. The platform shows a warning to copy the new embed code
2. Replace the old script tag on your website with the new one
3. Changes take effect immediately after the page refresh

**Note**: The embed code does NOT automatically update on external websites. You must manually update the code when configuration changes.

## Troubleshooting

### Button Not Appearing

- Verify the script URL is accessible
- Check browser console for errors
- Ensure `data-agent-id` is correct

### Call Not Connecting

- Verify the agent is active
- Check if daily limit is exceeded
- Ensure domain is in allowed list (if configured)

### Domain Validation Failing

- Add your domain to the allowed domains list
- Include both `example.com` and `www.example.com` if needed
- Subdomains are automatically allowed when parent domain is listed

## Related Documentation

- [Voice Agents Overview](./overview.md)
- [Implementation Plan](../../03_implementation/EMBED_CALL_BUTTON_PLAN.md)
- [Testing Guide](../../04_development_guides/testing.md)

# PRD: Chat Agents with Long-term Memory

**Feature:** Cloud-based AI Agents with Persistent Memory  
**Status:** Draft  
**Priority:** P0 (Highest)  
**Target:** VoiceAI Platform v2.0  
**Created:** 2026-02-28

---

## 1. Problem Statement

### Current State
- VoiceAI platform focuses on voice (phone) agents
- No solution for text-based chat agents
- No long-running agents with persistent memory
- Customers need "OpenClaw in the cloud" but easier to use

### Pain Points
1. **No Chat Channel:** Customers want agents on Slack, WhatsApp, Discord, web chat
2. **No Memory:** Agents forget everything between conversations
3. **Technical Setup:** OpenClaw requires technical setup (SSH, config, etc.)
4. **No Persistence:** Can't have agents that "remember" clients over time

---

## 2. Solution Overview

Build a **cloud-based AI agent platform** (like Letta/Agno) that provides:
- **Multi-channel:** Slack, WhatsApp, Discord, Web Chat, Telegram
- **Long-term Memory:** Persistent user context across conversations
- **Knowledge Bases:** RAG with company documentation
- **Easy Setup:** No-code configuration for non-technical users
- **Enterprise Ready:** RBAC, SSO, audit logs

### Target Users
- **SMBs:** Small businesses wanting AI assistants
- **Enterprises:** Internal copilots and customer service
- **Developers:** Teams wanting programmatic agent control

---

## 3. User Stories

| User | Story | Acceptance Criteria |
|------|-------|-------------------|
| Admin | I want to create a chat agent in 5 minutes | No-code setup, wizard-based |
| Admin | I want my agent to remember customer history | Persistent memory across sessions |
| Admin | I want to connect agent to Slack/WhatsApp | One-click channel integration |
| End User | I want to chat with AI that knows me | Personalized responses |
| Developer | I want API access to agents | REST API + WebSocket |

---

## 4. Technical Architecture

### 4.1 Framework Decision

**Option A: Agno (Recommended)**
- ✅ More mature, actively maintained
- ✅ Built-in AgentOS for multi-agent
- ✅ Multiple interfaces (A2A, AG-UI, Slack, WhatsApp)
- ✅ Knowledge bases with RAG
- ✅ Team/Workflow orchestration
- ✅ JWT/RBAC built-in
- ✅ Tracing and monitoring

**Option B: Letta**
- ✅ Better memory management (Context Repositories)
- ✅ Git-based memory versioning
- ❌ Less integrations than Agno
- ❌ Smaller community

**Recommendation:** Use **Agno** as the foundation, potentially extend with Letta's memory concepts.

### 4.2 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     VoiceAI Platform v2.0                       │
├─────────────────────────────────────────────────────────────────┤
│  User Interface (Next.js)                                      │
│  - Agent Builder (No-code)                                      │
│  - Chat Interface                                               │
│  - Analytics Dashboard                                          │
├─────────────────────────────────────────────────────────────────┤
│  Agent Runtime (Agno AgentOS)                                   │
│  - Single Agents                                                │
│  - Multi-agent Teams                                            │
│  - Workflows                                                    │
├─────────────────────────────────────────────────────────────────┤
│  Memory & Knowledge Layer                                       │
│  - PostgreSQL (Supabase) - Sessions, Messages                  │
│  - Vector DB (pgvector) - Knowledge Bases                       │
│  - Redis - Caching, Rate Limiting                              │
├─────────────────────────────────────────────────────────────────┤
│  Channel Integrations                                           │
│  - Slack App                                                    │
│  - WhatsApp Business API                                        │
│  - Discord Bot                                                  │
│  - Web Chat (Embeddable)                                        │
│  - Telegram Bot                                                │
│  - REST API                                                    │
├─────────────────────────────────────────────────────────────────┤
│  External Services                                              │
│  - LLM Providers (OpenAI, Anthropic, Google, Ollama)          │
│  - LiveKit (Voice - future)                                    │
│  - Webhook Services                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Database Schema

```sql
-- Chat Agents
CREATE TABLE chat_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    avatar_url VARCHAR(500),
    
    -- Agent Configuration
    model_provider VARCHAR(50),
    model_name VARCHAR(100),
    system_prompt TEXT,
    
    -- Capabilities
    capabilities JSONB DEFAULT '{"chat": true, "voice": false}',
    
    -- Memory Settings
    memory_enabled BOOLEAN DEFAULT true,
    memory_type VARCHAR(20) DEFAULT 'user',  -- 'user', 'session', 'organization'
    max_history_messages INTEGER DEFAULT 100,
    
    -- Knowledge Base
    knowledge_base_id UUID REFERENCES knowledge_bases(id),
    
    -- Status
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Agent Users (end users chatting with agents)
CREATE TABLE agent_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES chat_agents(id) ON DELETE CASCADE,
    external_id VARCHAR(255),  -- Slack user ID, WhatsApp number, etc.
    channel VARCHAR(20) NOT NULL,
    
    -- Memory
    user_memory JSONB,  -- Persistent user preferences
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(agent_id, external_id, channel)
);

-- Conversations
CREATE TABLE chat_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES chat_agents(id) ON DELETE CASCADE,
    agent_user_id UUID REFERENCES agent_users(id),
    
    status VARCHAR(20) DEFAULT 'active',
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    
    metadata JSONB  -- Channel info, campaign, etc.
);

-- Messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES chat_conversations(id) ON DELETE CASCADE,
    
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    
    -- For memory/summarization
    tokens INTEGER,
    is_important BOOLEAN DEFAULT false,
    
    metadata JSONB,  -- Attachments, tool calls, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

-- Knowledge Bases (RAG)
CREATE TABLE knowledge_bases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Embedding config
    embedding_provider VARCHAR(50),
    embedding_model VARCHAR(100),
    
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Knowledge Documents
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_base_id UUID REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    source_url VARCHAR(500),
    
    -- Embedding
    embedding VECTOR(1536),  -- Or dynamic dimension
    
    metadata JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Channel Integrations
CREATE TABLE agent_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES chat_agents(id) ON DELETE CASCADE,
    channel_type VARCHAR(20) NOT NULL,  -- 'slack', 'whatsapp', 'discord', 'web', 'telegram'
    
    -- Channel Configuration
    config JSONB NOT NULL,  -- Webhook URLs, tokens, etc.
    
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(agent_id, channel_type)
);

-- API Keys for Developers
CREATE TABLE agent_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES chat_agents(id) ON DELETE CASCADE,
    
    name VARCHAR(100),
    key_hash VARCHAR(255) NOT NULL,
    last_used_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.4 Core Services

```python
# Agent Service
class ChatAgentService:
    def __init__(self, db, llm_provider, memory_store):
        self.db = db
        self.llm = llm_provider
        self.memory = memory_store
    
    async def create_agent(self, config: AgentConfig) -> ChatAgent:
        """Create a new chat agent"""
        
    async def process_message(self, agent_id: str, user_id: str, 
                           message: str, channel: str) -> str:
        """Process incoming message and return response"""
        # 1. Load user memory
        # 2. Load conversation history
        # 3. Build context with knowledge base
        # 4. Call LLM
        # 5. Save to memory
        # 6. Return response
    
    async def get_conversation_history(self, agent_id, user_id, limit=50):
        """Get chat history with optional summarization"""
    
    async def search_knowledge(self, agent_id, query):
        """RAG-style knowledge search"""

# Memory Service
class MemoryService:
    def __init__(self, db):
        self.db = db
    
    async def get_user_memory(self, agent_id, external_id) -> dict:
        """Get persistent user preferences"""
    
    async def update_user_memory(self, agent_id, external_id, updates):
        """Update user memory with new information"""
    
    async def summarize_conversation(self, conversation_id) -> str:
        """Generate conversation summary"""
    
    async def extract_memories(self, messages) -> list[Memory]:
        """Extract important facts from messages"""

# Channel Service
class ChannelService:
    async def send_message(self, channel: str, user_id: str, message: str):
        """Send message to user via their channel"""
    
    async def register_webhook(self, channel: str, webhook_url: str):
        """Register webhook for channel events"""
    
    async def handle_incoming(self, channel: str, payload: dict) -> Message:
        """Parse incoming message from channel"""
```

### 4.5 Agno Integration

```python
# Agno Agent Setup
from agno import Agent, Knowledge, Storage
from agno.agent.os import AgentOS

# Agent with Memory
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    instructions=" customer support agent.",
You are a helpful    memory=True,  # Enables memory
    storage=Storage(
        table_name="agent_memories",
        db_url=supabase_url
    ),
    knowledge=Knowledge(
        vector_db=PGVector(
            table_name="knowledge_documents",
            embedder=OpenAIEmbedder()
        )
    ),
    tools=[
        # Custom tools
        search_knowledge,
        update_user_profile,
        schedule_appointment
    ]
)

# AgentOS for Production
agent_os = AgentOS(
    agents=[agent],
    middleware=[
        JWTMiddleware(api_key=...),
        LoggingMiddleware(),
        RateLimitMiddleware(max_requests=100)
    ]
)

# Run agent
response = agent.run("Hello, I need help with my order #12345")
```

---

## 5. UI/UX Specification

### 5.1 Agent Builder (No-code)

**Wizard Flow:**
1. **Basics:** Name, description, avatar
2. **Personality:** Tone, language, greeting
3. **Capabilities:** Tools, knowledge base, integrations
4. **Channels:** Select channels to enable
5. **Preview:** Test in chat

**Personality Builder:**
- Tone slider (Formal ↔ Casual)
- Language selector
- Custom greeting templates
- Response length preference

### 5.2 Chat Interface

**For End Users:**
- Clean chat UI (like ChatGPT)
- Typing indicators
- Message status (sent, delivered, read)
- Attachment support

**For Admins:**
- Live conversation monitoring
- Manual intervention button
- Force response
- End conversation

### 5.3 Analytics Dashboard

**Metrics:**
- Total conversations
- Messages per conversation
- Average response time
- Resolution rate
- User satisfaction ratings
- Cost per conversation

**Charts:**
- Conversations over time
- Messages by channel
- Top topics/queries
- Agent performance comparison

---

## 6. Channel Integrations

### 6.1 Slack
- DM with users
- Channel mentions
- Thread replies
- Slash commands
- App home tab

### 6.2 WhatsApp
- Business API integration
- Template messages
- Media support
- Read receipts

### 6.3 Discord
- Bot commands
- DM support
- Channel messages
- Embeds for rich responses

### 6.4 Web Chat
- Embeddable widget
- Custom branding
- Proactive chat
- Chat history

### 6.5 Telegram
- Bot API
- Inline queries
- Keyboard buttons

---

## 7. Security & Enterprise

### 7.1 Authentication
- Organization-level SSO (SAML, OIDC)
- API key management
- JWT for API access

### 7.2 Authorization
- Role-based access (Admin, Editor, Viewer)
- Agent-level permissions
- Channel-specific access

### 7.3 Compliance
- Data residency options
- Audit logs
- PII handling
- GDPR export

---

## 8. Phased Implementation

### Phase 1: Core Agent (4 weeks)
- Agent CRUD APIs
- Basic chat interface
- PostgreSQL storage
- Single channel (Web)

### Phase 2: Memory & Knowledge (3 weeks)
- User memory system
- Knowledge base + RAG
- Conversation summarization

### Phase 3: Channels (3 weeks)
- Slack integration
- WhatsApp integration
- Discord integration

### Phase 4: Enterprise (2 weeks)
- RBAC
- API keys
- Analytics
- Webhooks

---

## 9. Pricing Model

| Tier | Price | Features |
|------|-------|----------|
| Starter | $29/mo | 1 agent, 500 messages, Web chat |
| Professional | $99/mo | 5 agents, 10K messages, All channels |
| Enterprise | Custom | Unlimited, SSO, Dedicated |

---

## 10. Success Metrics

| Metric | Target (6 months) |
|--------|-------------------|
| Active Agents | 500+ |
| Monthly Messages | 1M+ |
| Channels Deployed | 1000+ |
| NPS Score | 50+ |
| Customer Retention | 90% |

---

## 11. Dependencies

- **Agno:** Agent runtime
- **Supabase:** Database + Auth
- **pgvector:** Vector embeddings
- **LiveKit:** Voice (future phase)
- **Slack/Discord/WhatsApp APIs:** Channel integrations

---

## 12. Comparison with Voice Agents

| Feature | Voice Agents | Chat Agents |
|---------|-------------|-------------|
| Channel | Phone | Slack, WhatsApp, Discord, Web |
| Interaction | Real-time voice | Async text/typing |
| Memory | Session-based | Long-term user memory |
| Complexity | High (voice, STT, TTS) | Medium (text) |
| Use Case | Phone support, sales | Customer service, internal copilot |

---

## 13. Open Questions

1. **Voice in Chat:** Should chat agents also support voice later?
2. **Multi-agent Teams:** Need orchestration of multiple agents?
3. **Custom Tools:** Allow users to define custom Python tools?
4. **Human Handoff:** How to escalate to human agents?
5. **A/B Testing:** Need experiment framework for prompts?

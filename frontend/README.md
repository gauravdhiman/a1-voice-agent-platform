# Frontend - Multi-Tenant SaaS Platform

Next.js frontend for the multi-tenant SaaS platform.

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- npm

### Installation

```bash
npm install
```

### Development

```bash
# Copy environment template
cp .env.local.example .env.local

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 🏗️ Architecture

### Tech Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: Shadcn/ui
- **Build Tool**: Turbopack (Next.js built-in)

### Directory Structure

```
src/
├── app/                    # App Router pages and layouts
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Home page
├── components/            # React components
│   ├── ui/                # Shadcn/ui base components
│   ├── auth/              # Authentication components
│   ├── dashboard/         # Dashboard-specific components
│   └── layout/            # Layout components
├── lib/                   # Utility libraries
│   ├── api/               # API client and configuration
│   └── utils.ts           # Shared utilities
├── types/                 # TypeScript type definitions
├── hooks/                 # Custom React hooks
└── services/              # Business logic and services
```

## 🎨 UI Components

Built with [Shadcn/ui](https://ui.shadcn.com/) for consistent, accessible components:

### Available Components

**UI Components**:
- Button
- Card
- Input
- Label
- Form
- Select
- Avatar
- Dropdown Menu

**Business Components**:
- **AgentCard** - Unified agent card with Edit/Tools/Delete buttons
- **AgentCreateWidget** - Multi-step agent creation wizard (Basic → Phone → Tools → Review)
- **ToolCard** - Tool cards with connection status visual feedback
- **ToolConfigDrawer** - Slide-in drawer for tool configuration
- **ToolDisconnectDialog** - Confirmation dialog for disconnecting tools
- **DeleteConfirmationDialog** - Generic delete confirmation modal
- **DeleteButton** - Reusable button with confirmation flow
- Navigation Menu

### Adding New Components

```bash
npx shadcn@latest add [component-name]
```

## 🔧 Configuration

### Environment Variables

Create `.env.local` from `.env.local.example`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=24x7 AI
NEXT_PUBLIC_APP_DESCRIPTION=Multi-tenant SaaS application template
```

### Next.js Configuration

Key configurations in `next.config.ts`:

- `output: 'standalone'` - Optimized for Docker deployment
- `optimizePackageImports` - Improved build performance

## 📦 Scripts

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server

# Code Quality
npm run lint         # Run ESLint
npm run type-check   # TypeScript type checking
```

## 🐳 Docker

### Development

```bash
# Build development image
docker build -f Dockerfile.dev -t saas-frontend-dev .

# Run development container
docker run -p 3000:3000 -v $(pwd):/app saas-frontend-dev
```

### Production

```bash
# Build production image
docker build -t saas-frontend .

# Run production container
docker run -p 3000:3000 saas-frontend
```

## 🔗 API Integration

The frontend includes a type-safe API client (`src/lib/api/client.ts`) that:

- Handles authentication tokens
- Provides typed request/response interfaces
- Includes error handling
- Supports all HTTP methods (GET, POST, PUT, DELETE)

### Usage Example

```typescript
import { apiClient } from "@/lib/api/client";

// Set auth token
apiClient.setAuthToken("your-jwt-token");

// Make API calls
const users = await apiClient.get<User[]>("/users");
const user = await apiClient.post<User>("/users", { name: "John" });
```

## 🎯 Type Safety

### Key Types (`src/types/index.ts`)

```typescript
interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  // ...
}

interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: "free" | "pro" | "enterprise";
  // ...
}

interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}
```

## 🚧 Development Guidelines

### Code Style

- Use TypeScript for all new files
- Follow ESLint configuration
- Use Tailwind CSS for styling
- Prefer function components with hooks

### Component Structure

```typescript
interface ComponentProps {
  // Define props
}

export function Component({ ...props }: ComponentProps) {
  // Component logic
  return (
    <div className="tailwind-classes">
      {/* JSX */}
    </div>
  );
}
```

### File Naming

- Components: `PascalCase.tsx`
- Utilities: `kebab-case.ts`
- Types: `index.ts` (in dedicated folders)

## 🔄 Next Steps

1. **Authentication UI**: Login/signup forms
2. **Dashboard Layout**: Multi-tenant dashboard
3. **State Management**: React Query integration
4. **Form Handling**: React Hook Form setup
5. **Testing**: Jest and React Testing Library
6. **Storybook**: Component documentation

## 📝 Skills System

The frontend supports a **platform skills fork/refresh model** for managing reusable AI capabilities:

- **Organization Skills Tab** (`/organization?tab=skills`): Split-view UI with a skill list on the left and content editor on the right. Supports creating custom skills, forking from platform templates, and importing from GitHub/skills.sh URLs.
- **Agent Skills Tab** (`/agents/{id}`): Toggle skills on/off per agent. Hidden skills still appear if assigned, with a "Hidden" badge and a quick action to show them in the library.
- **Platform Library Sheet**: Browse immutable platform skill templates. Filter by name/description. Fork into org library.
- **Refresh Confirmation Dialog**: Warns before overwriting all content and files with the latest platform version.

### Key Components

| Component | Location |
|-----------|----------|
| Skills Management | `src/app/(dashboard)/organization/page.tsx` |
| Agent Skill Assignment | `src/app/(dashboard)/agents/[agentId]/page.tsx` |
| Skill Service | `src/services/skill-service.ts` |
| Skill Types | `src/types/skill.ts` |

For the full architecture, see [Platform Skills Fork Model](../docs/03_implementation/platform_skills_fork_model.md).

## 🐛 Troubleshooting

### Common Issues

**Build Errors**

- Check TypeScript types are correctly defined
- Ensure all imports are valid
- Verify environment variables are set

**Docker Issues**

- Make sure Docker is running
- Check file permissions on volumes
- Verify port availability

**Hot Reload Not Working**

- Restart development server
- Check file watchers aren't at limit
- Verify volume mounting in Docker

---

For more information, see the main [project README](../README.md).

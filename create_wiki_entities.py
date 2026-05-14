"""Create wiki entity stubs in VaultNote table."""
import asyncio
from sqlalchemy import select
from atlas.db.session import get_session
from atlas.db.models import VaultNote

async def create_wiki_entities():
    """Create VaultNote entries for wiki entities referenced in links."""
    
    # Common wiki entities from your links
    wiki_entities = [
        "angular", "docker", "python", "obsidian", "react", "typescript",
        "javascript", "nodejs", "git", "github", "linux", "ubuntu",
        "postgresql", "redis", "fastapi", "nextjs", "d3", "tailwindcss",
        "markdown", "yaml", "json", "html", "css", "api", "rest",
        "graphql", "websocket", "sse", "jwt", "oauth", "ssl", "https",
        "ssh", "vpn", "docker-compose", "kubernetes", "nginx", "apache",
        "cloudflare", "vercel", "netlify", "aws", "gcp", "azure",
        "ollama", "groq", "deepseek", "openai", "anthropic", "claude",
        "gemini", "gpt", "llm", "ai", "ml", "embedding", "vector",
        "pgvector", "sqlite", "mongodb", "firebase", "supabase",
        "pwa", "ios", "android", "react-native", "flutter", "electron",
        "tauri", "desktop", "mobile", "web", "app", "saas",
        "stripe", "paypal", "payment", "subscription", "billing",
        "analytics", "metrics", "logging", "monitoring", "alerting",
        "ci", "cd", "devops", "gitops", "iac", "terraform", "ansible",
        "prometheus", "grafana", "elk", "sentry", "datadog",
        "testing", "jest", "pytest", "cypress", "playwright", "selenium",
        "unit-test", "integration-test", "e2e-test", "tdd", "bdd",
        "agile", "scrum", "kanban", "sprint", "backlog", "roadmap",
        "mermaid", "plantuml", "diagram", "chart", "graph", "visualization",
        "note-taking", "knowledge-management", "pkm", "zettelkasten",
        "backlink", "wikilink", "tag", "metadata", "frontmatter",
        "moc", "index", "hub", "map-of-content", "daily-note", "weekly-note",
        "goal", "task", "todo", "habit", "routine", "schedule", "calendar",
        "meeting", "note", "idea", "concept", "term", "definition",
        "book", "article", "paper", "research", "study", "learning",
        "course", "tutorial", "guide", "documentation", "reference",
        "snippet", "code", "script", "function", "component", "module",
        "library", "package", "dependency", "import", "export", "require",
        "async", "await", "promise", "callback", "event", "stream", "buffer",
        "file", "path", "directory", "folder", "storage", "disk", "memory",
        "cache", "session", "cookie", "localstorage", "indexeddb",
        "browser", "chrome", "firefox", "safari", "edge", "extension",
        "devtools", "console", "debugger", "breakpoint", "profiler",
        "error", "exception", "stack-trace", "bug", "issue", "ticket",
        "pr", "commit", "branch", "merge", "rebase", "cherry-pick",
        "conflict", "resolution", "review", "approve", "deploy",
        "staging", "production", "development", "localhost", "127.0.0.1",
        "0.0.0.0", "port", "socket", "tcp", "udp", "http", "http2", "http3",
        "dns", "cdn", "load-balancer", "reverse-proxy", "gateway",
        "microservice", "monolith", "serverless", "lambda", "function-as-a-service",
        "container", "image", "registry", "artifact", "build", "artifact",
        "pipeline", "workflow", "job", "step", "action", "runner",
        "secret", "env", "variable", "config", "settings", "preference",
        "permission", "role", "user", "account", "profile", "avatar",
        "authentication", "authorization", "authn", "authz", "identity",
        "mfa", "2fa", "totp", "backup-code", "recovery", "reset",
        "password", "passphrase", "key", "token", "certificate",
        "encryption", "hash", "salt", "pepper", "bcrypt", "argon2",
        "cors", "csp", "xss", "csrf", "sql-injection", "nosql-injection",
        "rate-limit", "throttle", "quota", "ddos", "waf", "firewall",
        "penetration-test", "vulnerability", "cve", "exploit", "patch",
        "backup", "restore", "snapshot", "archive", "export", "import",
        "migration", "upgrade", "downgrade", "rollback", "hotfix",
        "feature-flag", "experiment", "ab-test", "canary", "blue-green",
        "dark-launch", "soft-launch", "beta", "alpha", "rc", "stable",
        "lts", "deprecated", "obsolete", "legacy", "modern", "current",
        "future", "planned", "proposed", "draft", "wip", "todo", "done",
        "blocked", "in-progress", "review", "qa", "testing", "ready",
        "shipped", "released", "published", "public", "private", "internal",
        "external", "partner", "customer", "client", "user", "admin",
        "moderator", "editor", "viewer", "guest", "anonymous",
        "free", "paid", "premium", "enterprise", "team", "personal",
        "starter", "basic", "pro", "business", "organization", "workspace",
    ]
    
    async with get_session() as session:
        # Get existing wiki paths
        existing = await session.execute(
            select(VaultNote.path).where(VaultNote.vault == 'wiki')
        )
        existing_paths = {row[0] for row in existing.all()}
        print(f"Existing wiki entries: {len(existing_paths)}")
        
        new_entries = 0
        for entity in wiki_entities:
            path = f"wiki/entities/{entity}.md"
            if path in existing_paths:
                continue
            
            note = VaultNote(
                path=path,
                title=entity.replace('-', ' ').title(),
                vault='wiki',
                node_type='entity'
            )
            session.add(note)
            new_entries += 1
        
        if new_entries > 0:
            await session.commit()
            print(f"Added {new_entries} new wiki entity entries")
        else:
            print("No new wiki entities needed")

if __name__ == "__main__":
    asyncio.run(create_wiki_entities())

## Development Guide

### Setup

**Prerequisites:**
```bash
# Frappe Framework requirements
python >= 3.8
node >= 16.x
npm >= 8.x
mariadb >= 10.3
redis-server

# For development with SQLite
sqlite3
```

**Frappe Bench Installation:**
```bash
# Install Frappe bench
pip install frappe-bench

# Create new site
bench new-site beam.local
bench get-app beam https://github.com/agritheory/beam.git
bench --site beam.local install-app beam

# Start development
bench start
```

**Frontend Development Setup:**
```bash
# Navigate to Beam app
cd apps/beam

# Install Node dependencies
npm install

# Start Vite development server with HMR
npm run dev

# Build for production
npm run build

# Register Beam resolvers
npm run register
```

**Environment Configuration:**
```python
# site_config.json
{
    "db_name": "beam_development",
    "db_password": "password",
    "developer_mode": 1,
    "auto_reload": 1,
    "disable_website_cache": 1
}
```

**Development Workflow:**
```bash
# Backend development (Python/Frappe)
bench start

# Frontend development (Vue/TypeScript)
npm run dev

# Watch mode for frontend builds
npm run build:watch
```

**Scan Matrix Development:**
- Edit `/beam/scan/__init__.py` for scan logic
- Modify `listview` and `frm` dictionaries for action definitions
- Use `beam_listview` and `beam_frm` hooks for custom overrides
- Test scan actions via Beam PWA interface

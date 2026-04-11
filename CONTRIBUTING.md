# Contributing to Ops Safety System

Thank you for your interest in contributing to the Ops Safety System! This document outlines guidelines and procedures for contributing.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm 9+
- Git

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/CodeReCet.git
   cd CodeReCet
   ```

2. **Set up the backend**
   ```powershell
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```

3. **Set up the frontend**
   ```powershell
   cd frontend
   npm install
   copy .env.example .env
   ```

4. **Run locally**
   - Backend: `uvicorn app.main:app --reload`
   - Frontend: `npm run dev`

## Development Workflow

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/add-google-ai-integration`
- `bugfix/fix-stream-timeout`
- `docs/update-deployment-guide`

### 2. Make Your Changes

- Backend: Python + FastAPI
- Frontend: React + TypeScript + Vite
- Keep code clean and well-documented

### 3. Test Your Changes

**Backend tests:**
```powershell
cd backend
pytest -v
```

**Frontend build:**
```powershell
cd frontend
npm run build
```

### 4. Commit and Push

```bash
git add .
git commit -m "feat: add new feature"
git push origin feature/your-feature-name
```

Use conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `style:` code format
- `refactor:` code reorganization
- `test:` test additions
- `chore:` maintenance

### 5. Submit a Pull Request

- Provide a clear description
- Reference any related issues
- Ensure tests pass

## Reporting Issues

Use GitHub Issues to report bugs or suggest features:
- **Bug Report**: Include steps to reproduce, expected behavior, and actual behavior
- **Feature Request**: Explain the use case and expected benefits

## Project Structure

```
CodeReCet/
├── backend/               # FastAPI server
│   ├── app/              # Application code
│   ├── models/           # ML models
│   ├── scripts/          # Helper scripts
│   ├── tests/            # Unit tests
│   └── requirements.txt   # Python dependencies
├── frontend/             # React + Vite app
│   ├── src/              # React components
│   ├── public/           # Static assets
│   └── package.json      # Node dependencies
├── n8n/                  # Workflows
├── DEPLOYMENT.md         # Deployment guide
└── README.md             # Project README
```

## Coding Standards

### Backend (Python)
- Use type hints
- Follow PEP 8
- Write docstrings
- Keep functions small and focused

### Frontend (TypeScript/React)
- Use functional components with hooks
- Write prop types
- Keep components reusable
- Use meaningful variable names

## Google Solutions Challenge Integration

This project is being developed for the **Google Solutions Challenge** under the theme **Rapid Crisis Response**.

Key requirements:
- [ ] Cloud deployment (Render/GCP)
- [ ] Google AI integration (Gemini/Vertex AI)
- [ ] Crisis response capabilities
- [ ] Real-time monitoring

If contributing to these areas, please:
1. Ensure Google API keys are never committed
2. Use environment variables for configuration
3. Test with mock AI responses before using real APIs
4. Document any new Google service integrations

## Questions?

- Check existing issues
- Review [DEPLOYMENT.md](./DEPLOYMENT.md) for setup help
- Open a discussion for questions

Thank you for contributing!

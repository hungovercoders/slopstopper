# Slopstopper

SlopStopper — a static site promoting deterministic feedback for AI-driven development, with automated Netlify deployment and feature branch preview support.

The live site is at [https://griff-template.netlify.app/](https://griff-template.netlify.app/).

## Features

- 🛡️ SlopStopper: deterministic feedback for AI-driven development
- 🚀 Automated deployment to Netlify via GitHub Actions
- 🔄 Feature branch preview deployments for PRs
- 💻 Local development server

## 📚 Documentation

This project follows a structured documentation framework. For comprehensive navigation and to find specific topics:

**→ [Documentation Hub (index.md)](index.md)** - Central navigation for all project documentation

> **Note**: The categories defined in [index.md](index.md) drive naming conventions across the project—local tasks use `category:action` format, CI/CD workflows use `category-action-check.yml` format.

## Installing the Tooling into Another Repository

You can install the SlopStopper tooling (Taskfile tasks, analysis scripts, and
generic GitHub Actions workflows) into any existing repository.

**Recommended two-step approach** (review the script before running):

```bash
curl -fsSL https://raw.githubusercontent.com/happydevs-studio/template-netlify/main/install.sh -o install.sh
bash install.sh [TARGET_DIR]
```

Or, if you already have this repo checked out, use the Task runner:

```bash
task install TARGET=/path/to/your-repo
```

**What gets installed:**

| Item | Description |
|------|-------------|
| `Taskfile.yml` | All task definitions (`task --list` to see them) |
| `.scripts/` | Python/shell analysis scripts used by the tasks |
| `.github/workflows/` | Hygiene, security, and reliability workflows |
| `package.json` | Created (or `devDependencies` merged into an existing file) |

Existing files are never overwritten — remove them first if you want to
reinstall.

**After installing**, run:

```bash
# 1. Install Task runner (if you don't have it)
curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin

# 2. Install npm dependencies
npm install

# 3. See all available tasks
task --list
```

## Quick Start

### Running Locally

1. Clone the repository:
```bash
git clone https://github.com/happydevs-studio/template-netlify.git
cd template-netlify
```

2. Start the local development server:
```bash
npm start
```

This runs `node server.js`, which starts a local HTTP server on port 8080 that reads security headers from `netlify.toml` to match production behavior.

Alternatively, you can open `app/index.html` directly in your browser (note: JS interactions require the compiled files from `npm run build`).

## Local Development

### Prerequisites

- **Task** (task runner): Install from [taskfile.dev](https://taskfile.dev/)
  ```bash
  curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin
  ```

### Available Tasks

All development tasks can be run with the `task` command. View available tasks:

```bash
task --list
```

### Code Complexity Analysis

Analyze code complexity locally using Lizard:

```bash
task hygiene:complexity
```

This will:
- Automatically install Lizard if not already installed
- Analyze the codebase for cyclomatic complexity
- Generate both human-readable and CSV reports in `.complexity-reports/`
- Display a summary with any high-complexity items (CCN > 10)

**Reports location**: `.complexity-reports/`
- `complexity-report.md` - Human-readable Markdown report
- `complexity-report.csv` - Machine-readable format for processing

**Complexity guidelines for this template:**
- Functions with cyclomatic complexity (CCN) > 10 should be simplified
- Keep functions under 50 lines when possible
- For this static template, code should remain minimal

The same analysis runs in CI/CD on pull requests and pushes to `main`.

**For customizing complexity thresholds or configuration:**
See [hygiene/COMPLEXITY_CONFIG.md](hygiene/COMPLEXITY_CONFIG.md) for detailed setup instructions, threshold customization, and troubleshooting.

## Netlify Setup

### Prerequisites

1. A Netlify account (sign up at [netlify.com](https://www.netlify.com))
2. A GitHub repository with this code

### Initial Netlify Site Setup

1. **Create a new site on Netlify:**
   - Log in to your Netlify account
   - Go to "Sites" and click "Add new site"
   - Choose "Import an existing project"
   - Connect to your GitHub repository
   - For build settings:
     - Build command: Leave empty or use `echo 'No build required'`
     - Publish directory: `.` (current directory)
   - Click "Deploy site"

2. **Get your Netlify credentials:**
   - **NETLIFY_SITE_ID**: 
     - Go to Site settings → General → Site details
     - Copy the "Site ID" (also called "API ID")
   
   - **NETLIFY_AUTH_TOKEN**:
     - Go to your Netlify User settings → Applications → Personal access tokens
     - Click "New access token"
     - Give it a descriptive name (e.g., "GitHub Actions Deploy")
     - Copy the generated token (save it securely, you won't see it again!)

3. **Add secrets to your GitHub repository:**
   - Go to your GitHub repository
   - Navigate to Settings → Secrets and variables → Actions
   - Click "New repository secret" and add:
     - Name: `NETLIFY_AUTH_TOKEN`, Value: (your Netlify personal access token)
     - Name: `NETLIFY_SITE_ID`, Value: (your Netlify site ID)

## Deployment Workflow

### Production Deployment

The site automatically deploys to production when changes are pushed to the `main` branch:

1. Make your changes locally
2. Commit and push to `main`:
```bash
git add .
git commit -m "Your commit message"
git push origin main
```

3. GitHub Actions will automatically deploy to your production Netlify site
4. A commit comment will be added with the deployment URL

### Feature Branch Preview Deployment

When you create a pull request, a preview deployment is automatically created:

1. Create a new feature branch:
```bash
git checkout -b feature/my-new-feature
```

2. Make your changes and push:
```bash
git add .
git commit -m "Add new feature"
git push origin feature/my-new-feature
```

3. Create a Pull Request on GitHub

4. GitHub Actions will automatically:
   - Deploy a preview version of your site
   - Add a comment to the PR with the preview URL
   - Each new commit to the PR will update the preview

5. Review the preview deployment before merging

6. Once merged to `main`, the changes will be deployed to production

## Project Structure

```
template-netlify/
├── .github/
│   └── workflows/           # GitHub Actions workflows
├── docs/                    # Project documentation
│   ├── index.md             # Documentation hub and governance
│   ├── architecture/
│   ├── contributing/
│   ├── decisions/
│   ├── deployment/
│   ├── hygiene/
│   ├── reliability/
│   ├── runbooks/
│   └── security/
├── tests/                   # Playwright and other tests
├── app/                     # Static site: HTML, CSS, compiled JS (publish dir)
│   ├── index.html           # SlopStopper home page
│   ├── index.css            # Home styles
│   ├── features.html        # Features page
│   ├── features.css         # Features styles
│   ├── tools.html           # Tools page
│   └── tools.css            # Tools styles
├── src/                     # TypeScript source files
│   ├── index.ts             # Home interaction (compiled → app/index.js)
│   ├── features.ts          # Features interaction (compiled → app/features.js)
│   └── tools.ts             # Tools interaction (compiled → app/tools.js)
├── server.js                # Local dev server (reads netlify.toml headers, serves app/)
├── netlify.toml             # Netlify configuration
├── tsconfig.json            # TypeScript configuration
├── package.json             # NPM config and dev dependencies
├── playwright.config.js     # Playwright test configuration
└── Taskfile.yml             # Task runner definitions
```

## Configuration Files

### netlify.toml

Configures Netlify build and deployment settings. The publish directory is `app/` and the build command runs `npm run build` (TypeScript compilation).

### .github/workflows/netlify-deploy.yml

GitHub Actions workflow that:
- Triggers on pushes to `main` (production deployment)
- Triggers on pull requests to `main` (preview deployment)
- Uses the `nwtgck/actions-netlify` action for deployment
- Adds deployment URLs as comments on PRs

## Troubleshooting

### Local Server Issues

- **Port already in use**: If port 8080 is already in use, the server will try another port automatically
- **npm not found**: Install Node.js from [nodejs.org](https://nodejs.org/)

### Deployment Issues

- **Deployment fails with "Unauthorized"**: Check that your `NETLIFY_AUTH_TOKEN` is correct
- **Deployment fails with "Site not found"**: Verify your `NETLIFY_SITE_ID` is correct
- **No preview comment on PR**: Ensure the GitHub Actions workflow has write permissions

## Agent Instructions

For instructions on project conventions, deployment workflows, and best practices intended for AI agents and automation tools, see [AGENTS.md](AGENTS.md) in the docs directory. This is an open standard that applies across all tooling.

## License

MIT

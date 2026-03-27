# Sensei

AI-powered code review CLI for GitLab Merge Requests. Sensei learns your review style from past comments and applies it consistently to new MRs using Claude as the review engine.

## What it does

1. **Learns your style** — Scrapes your past GitLab review comments, analyzes tone/priorities/patterns, and builds a reusable style profile.
2. **Reviews MRs** — Fetches diffs, reads full file context, and generates review comments that match your voice.
3. **Posts intelligently** — Must-fix issues go inline on the exact line. Nits get grouped into one summary comment. Test coverage gaps get a single consolidated table.

## Prerequisites

- Python 3.9+
- [Claude Code CLI](https://claude.ai/code) installed and authenticated
- A GitLab personal access token with `api` scope

## Install

From PyPI:

```bash
pip install sensei-review
```

Or from source:

```bash
git clone https://github.com/pulkit004/sensei.git && cd sensei
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Setup

```bash
# Initialize with your GitLab credentials
sensei init --pat <your-gitlab-pat>

# Learn your review style (scrapes last 365 days of comments)
sensei learn
```

Config is stored at `~/.sensei/` with restricted permissions (0600).

## Usage

```bash
# Review a single MR
sensei review https://gitlab.com/org/project/-/merge_requests/123

# Dry run (preview without posting)
sensei review https://gitlab.com/org/project/-/merge_requests/123 --dry-run

# Review multiple MRs in parallel
sensei review-batch --file mrs.txt

# Or pass URLs directly
sensei review-batch \
  https://gitlab.com/org/project/-/merge_requests/123 \
  https://gitlab.com/org/project/-/merge_requests/456

# Control concurrency (default 3, max 10)
sensei review-batch --file mrs.txt --concurrency 5

# Dry run batch
sensei review-batch --file mrs.txt --dry-run
```

The `--file` option reads MR URLs from a text file (one per line, `#` comments and blank lines ignored).

After review, you're prompted to **approve** (post to GitLab), **edit** (save to file for manual editing), or **discard**. In batch mode, results are shown sequentially after all reviews complete.

## Comment types

| Type | Confidence | How it's posted |
|------|-----------|-----------------|
| **Must-fix** | >= 90% | Inline on the exact diff line |
| **Nit** | 80-89% | Grouped into one summary comment |
| **Test gap** | any | Consolidated into a single test coverage table |

Comments below 80% confidence are dropped.

## Project rules

Sensei loads rules from multiple sources (in order):

1. `~/.sensei/rules/{org_project}.md` — Per-project rules you write
2. `CLAUDE.md` — From the repo being reviewed
3. `.claude/rules.md` — From the repo
4. `CODING_PRINCIPLES.md` — From the repo

## How the review works

Each file is reviewed in two phases:

1. **Code review** — Bugs, type safety, naming, architecture, security
2. **Silent failure hunting** — Only runs if the diff has error handling patterns (try/catch, optional chaining, etc.)

Files are reviewed in parallel (up to 8 concurrent workers, configurable batch size).

## Development

```bash
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v          # Run tests
pytest tests/ -v -x       # Stop on first failure
```

## Project structure

```
src/sensei/
  cli.py            # Click CLI commands
  config.py         # ~/.sensei config management
  gitlab_client.py  # GitLab API (diffs, file content, posting comments)
  reviewer.py       # Review prompts, parsing, consolidation
  learner.py        # Style profile learning from past comments
  formatter.py      # Comment formatting for terminal and GitLab
tests/              # Unit and integration tests
```

## License

MIT — see [LICENSE](LICENSE) for details.

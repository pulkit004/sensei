from pathlib import Path
import click


@click.group()
def main():
    """setu-review: AI-powered GitLab MR reviewer."""
    pass


@main.command()
@click.option("--pat", prompt="GitLab PAT", hide_input=True, help="Your GitLab Personal Access Token")
@click.option("--url", default="https://gitlab.com", help="GitLab instance URL")
def init(pat, url):
    """Initialize setu-review with your GitLab credentials."""
    from setu_review.config import init_config
    init_config(gitlab_pat=pat, gitlab_url=url)
    click.echo("Config saved to ~/.setu-review/config.yaml")


@main.command()
def learn():
    """Scrape your GitLab comments and build a review style profile."""
    click.echo("learn command - not yet implemented")


@main.command()
@click.argument("mr_url")
def review(mr_url):
    """Review a GitLab Merge Request."""
    click.echo(f"review command for {mr_url} - not yet implemented")


if __name__ == "__main__":
    main()

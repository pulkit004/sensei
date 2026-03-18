import click


@click.group()
def main():
    """setu-review: AI-powered GitLab MR reviewer."""
    pass


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

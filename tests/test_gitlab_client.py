from setu_review.gitlab_client import parse_mr_url


def test_parse_mr_url_standard():
    project, mr_iid = parse_mr_url(
        "https://gitlab.com/brokentusk/facade/ashpd/-/merge_requests/123"
    )
    assert project == "brokentusk/facade/ashpd"
    assert mr_iid == 123


def test_parse_mr_url_with_trailing_slash():
    project, mr_iid = parse_mr_url(
        "https://gitlab.com/brokentusk/facade/ashpd/-/merge_requests/123/"
    )
    assert project == "brokentusk/facade/ashpd"
    assert mr_iid == 123


def test_parse_mr_url_nested_group():
    project, mr_iid = parse_mr_url(
        "https://gitlab.com/brokentusk/facade/docs-mdx/-/merge_requests/45"
    )
    assert project == "brokentusk/facade/docs-mdx"
    assert mr_iid == 45

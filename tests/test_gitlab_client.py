from setu_review.gitlab_client import parse_mr_url, extract_diff_lines


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


def test_extract_diff_lines():
    diff = """@@ -10,6 +10,8 @@ some context
 unchanged line
+added line 11
+added line 12
 unchanged line
-removed line
 unchanged line"""
    lines = extract_diff_lines(diff)
    assert 11 in lines
    assert 12 in lines
    assert 10 not in lines  # context line, not added

from setu_review.learner import chunk_comments, build_analysis_prompt


def test_chunk_comments_respects_batch_size():
    comments = [{"body": f"comment {i}", "mr_url": f"url/{i}"} for i in range(10)]
    chunks = chunk_comments(comments, batch_size=3)
    assert len(chunks) == 4  # 3+3+3+1
    assert len(chunks[0]) == 3
    assert len(chunks[-1]) == 1


def test_build_analysis_prompt_includes_comments():
    comments = [
        {"body": "Use early returns here", "mr_url": "url/1", "file_path": "src/foo.py"},
        {"body": "Naming: prefer snake_case", "mr_url": "url/2", "file_path": "src/bar.py"},
    ]
    prompt = build_analysis_prompt(comments)
    assert "Use early returns here" in prompt
    assert "snake_case" in prompt

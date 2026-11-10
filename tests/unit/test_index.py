import pytest

from s3pypi.index import Hash, Index


@pytest.fixture(
    scope="function",
    params=[
        (
            "s3pypi",
            [
                f"s3pypi-{version}{suffix}"
                for version in (
                    "0",
                    "0!0",
                    "0+local",
                    "0.0",
                    "0.1.1",
                    "0.1.2",
                    "0.dev0",
                    "0.post0",
                    "0a0",
                    "0rc0",
                )
                for suffix in (
                    ".tar.gz",
                    "-py2-none-any.whl",
                )
            ],
            [Hash("sha256", "1234" * 16) if i % 3 == 0 else None for i in range(0, 20)],
        )
    ],
)
def index_html(request, data_dir):
    index_name, names, hashes = request.param
    filenames = dict(zip(names, hashes))
    with open(data_dir / "index" / f"{index_name}.html") as f:
        html = f.read().strip()
        yield html, filenames


def test_parse_index(index_html):
    html, expected_filenames = index_html
    index = Index.parse(html)
    assert index.filenames == expected_filenames


def test_render_index(index_html):
    expected_html, filenames = index_html
    html = Index(filenames).to_html()
    assert html == expected_html


def test_render_index_escapes_special_chars_in_filenames():
    filenames = {
        "a&b.tar.gz": None,
        "x<y>-1.0-py3-none-any.whl": Hash("sha256", "1" * 64),
    }
    html = Index(filenames).to_html()
    assert "a&amp;b.tar.gz" in html
    assert "x&lt;y&gt;-1.0-py3-none-any.whl" in html
    assert Index.parse(html).filenames == filenames

from pathlib import Path

import pytest

SAMPLE = '4\n2\n1 2\n3 4\n5 4\n3\n1 1 1\n2 2 2\n3 3 3\n4\n1 2 1 2\n3 3 2 2\n5 5 5 5\n5\n1 4 2 3 5\n6 4 5 7 6\n7 5 8 10 10'


def test_saved_html_keeps_sample_lines_math_and_unicode():
    from app.ingestion import import_html

    result = import_html(Path('tests/fixtures/statement.html').read_bytes())
    assert result.title == 'C. Тест снеговиков'
    assert result.samples[0].stdin == SAMPLE
    assert result.samples[0].stdout == '4\n27\n0\n10'
    assert '$$$a \\lt b \\lt c$$$' in result.statement
    assert '$$$1 \\le n \\le 5000$$$' in result.statement
    assert 'Первый шар\nВторой шар' in result.statement
    assert 'x^{2} + a_{i}' in result.statement
    assert 'SCRIPT' not in result.statement
    assert 'UNRELATED' not in result.statement


def test_recovers_rendered_tex_once_and_warns_image_math():
    from app.ingestion import import_html

    data = b'<div class="problem-statement"><p><span class="MathJax">RENDERED_DUPLICATE</span><script type="math/tex">a &lt; b</script><img src="https://bad.invalid/math.png"></p></div>'
    result = import_html(data)
    assert '$$$a < b$$$' in result.statement
    assert 'RENDERED_DUPLICATE' not in result.statement
    assert result.warnings


def test_incomplete_samples_warn_without_fabricating_answers():
    from app.ingestion import import_html

    result = import_html(b'<div class="problem-statement"><p>Find the answer.</p><div class="sample-test"><div class="input"><pre>1<br>2</pre></div></div></div>')
    assert not result.samples
    assert any('sample' in warning.lower() for warning in result.warnings)


@pytest.mark.parametrize('data', [b'<p>Missing statement</p>', b'\xff\xfeBAD', b'x' * (5 * 1024 * 1024 + 1)], ids=['missing', 'bad-encoding', 'oversized'])
def test_bad_imports_are_explicit_errors(data):
    from app.ingestion import ImportError as StatementImportError, import_html

    with pytest.raises(StatementImportError):
        import_html(data)


def test_declared_windows1251_is_decoded_without_replacement():
    from app.ingestion import import_html

    html = '<meta charset="windows-1251"><div class="problem-statement"><p>Входные данные.</p></div>'
    assert 'Входные данные.' in import_html(html.encode('cp1251')).statement


def test_real_sample_is_checked_locally_when_present():
    from app.ingestion import import_html

    path = Path('/Users/andreyryzhanskiy/Downloads/Задача - C - Codeforces.html')
    if not path.exists():
        return  # Personal page is optional; synthetic fixture always covers exact lines.
    result = import_html(path.read_bytes())
    assert result.samples[0].stdin == SAMPLE
    assert result.samples[0].stdout == '4\n27\n0\n10'
    assert 'a  \\lt  b  \\lt  c' in result.statement
    assert '5000' in result.statement

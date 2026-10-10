"""Extract saved statements as text without executing or fetching any content."""
import html
import re

from bs4 import BeautifulSoup
from pydantic import ValidationError

from app.contracts import ProblemInput, SamplePair


class ImportError(ValueError):
    pass


def decode(data: bytes) -> str:
    if len(data) > 5 * 1024 * 1024:
        raise ImportError('HTML exceeds the 5 MiB limit')
    declaration = re.search(br'charset\s*=\s*["\']?([A-Za-z0-9_-]+)', data[:4096], re.I)
    encoding = declaration.group(1).decode('ascii').lower() if declaration else 'utf-8-sig'
    allowed = {'utf-8', 'utf8', 'utf-8-sig', 'windows-1251', 'cp1251', 'windows-1252', 'iso-8859-1'}
    if encoding not in allowed:
        raise ImportError('Unsupported declared encoding; save the page as UTF-8')
    try:
        return data.decode(encoding, errors='strict')
    except UnicodeDecodeError as error:
        raise ImportError('Cannot decode HTML without losing characters') from error


def text(node) -> str:
    # Work on a private parsed copy; sample extraction must not alter the body.
    copy = BeautifulSoup(str(node), 'html.parser')
    for tag in copy.find_all('br'):
        tag.replace_with('\n')
    for tag in copy.find_all(['sup', 'sub']):
        tag.replace_with(('^' if tag.name == 'sup' else '_') + '{' + tag.get_text() + '}')
    for tag in copy.find_all(['p', 'div', 'li', 'pre', 'h1', 'h2', 'h3', 'ul', 'ol']):
        tag.insert_before('\n')
        tag.append('\n')
    lines = []
    for line in copy.get_text().splitlines():
        parts = re.split(r'(\$\$\$.*?\$\$\$)', line)
        lines.append(''.join(part if part.startswith('$$$') else re.sub(r'[\t \xa0]+', ' ', part) for part in parts).strip())
    return '\n'.join(line for line in lines if line)


def import_html(data: bytes) -> ProblemInput:
    document = BeautifulSoup(decode(data), 'html.parser')
    statement = document.select_one('.problem-statement')
    if statement is None:
        raise ImportError('No Codeforces .problem-statement section found')
    warnings = []
    for script in list(statement.find_all('script')):
        if script.get('type', '').startswith('math/tex'):
            script.replace_with('$$$' + html.unescape(script.get_text()) + '$$$')
        else:
            script.decompose()
    for annotation in list(statement.find_all('annotation', attrs={'encoding': 'application/x-tex'})):
        parent = annotation.find_parent('math')
        if parent:
            parent.replace_with('$$$' + annotation.get_text() + '$$$')
    for node in statement.select('.MathJax, .MathJax_Display, .MathJax_Preview, .katex-html, mjx-container, style, iframe, object'):
        node.decompose()
    if statement.find('img'):
        warnings.append('Images may contain formulas or essential information; review and correct the extracted text.')
    for image in statement.find_all('img'):
        image.replace_with('[image: ' + image.get('alt', 'review original page') + ']')
    samples = []
    for sample in statement.select('.sample-test'):
        inputs = sample.select('.input pre')
        outputs = sample.select('.output pre')
        if len(inputs) != len(outputs) or not inputs:
            warnings.append('Incomplete sample pair; enter both sample input and output before running.')
        for inp, out in zip(inputs, outputs):
            try:
                samples.append(SamplePair(stdin=text(inp), stdout=text(out)))
            except ValidationError:
                warnings.append('Empty or oversized sample; correct it before running.')
    for selector, label in [('.input-specification', 'input specification'), ('.output-specification', 'output specification')]:
        if not statement.select_one(selector):
            warnings.append('Missing ' + label + '; review the extracted statement.')
    if not samples:
        warnings.append('No complete samples extracted; add explicit sample input/output pairs.')
    title_node = statement.select_one('.header .title')
    try:
        return ProblemInput(title=text(title_node) if title_node else '', statement=text(statement), samples=samples, warnings=list(dict.fromkeys(warnings)))
    except ValidationError as error:
        raise ImportError('Extracted statement is empty or exceeds supported limits') from error

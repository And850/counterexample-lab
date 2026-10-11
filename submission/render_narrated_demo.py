"""Render recorded evidence and actual source with labeled macOS narration."""
import json
from pathlib import Path
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont


def duration(path):
    return float(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(path),
    ], text=True))


def main():
    result = json.loads(Path('submission/evidence-day2-gemini.json').read_text())
    evidence = result['evidence']
    assert result['outcome'] == 'corroborated_counterexample'
    assert evidence['references_agree'] and evidence['validators_agree']
    source = Path('app/search.py').read_text().splitlines()
    line = next(i for i, s in enumerate(source) if s.strip() ==
                'if not evidence.validators_agree or not evidence.references_agree:')
    excerpt = textwrap.dedent('\n'.join(source[line:line+2]))
    root = Path('.runs/narrated-demo')
    root.mkdir(parents=True, exist_ok=True)
    slides = [
        ('Find the input that breaks it',
         'Counterexample Lab | AI for Automation\n\n'
         'Competitive programming: samples pass, but an algorithm is wrong.\n'
         'Automate the search and execute the evidence.\n\n'
         'Recorded evidence and source walkthrough.\n'
         'Narration uses the Mac\'s built-in synthesized voice.',
         'After six years of competitive programming, finding a counterexample can still take longer than writing a solution. AI often suggests inputs without testing them. Counterexample Lab automates the search and executes the evidence. This is a recorded evidence and source walkthrough, with synthesized narration.'),
        ('Inputs and the hidden bug',
         'Problem: sum two integers in [-100, 100].\nSample: 2 3 -> 5\n\n'
         'Submitted bug: std::cout << std::abs(a + b);\n\n'
         'The app accepts pasted statements or saved Codeforces HTML.\n'
         'Review extracted math, constraints and editable samples.\n'
         'Paste C++17 code or upload a .cpp file.',
         'This deliberately wrong C plus plus program prints the absolute value of the sum. Two and three still produce five, so the sample passes. The interface accepts pasted statements or saved Codeforces HTML, with editable samples. Paste your C plus plus seventeen solution or upload its source file.'),
        ('The automated testing workflow',
         'AI generates parse, render, valid, solve, generate and shrink.\n'
         'Check every sample, input round trip and generator mode.\n\n'
         'Search tiny exhaustive, random and adversarial cases.\n'
         'Separate restricted Docker roles execute all code.\n\n'
         'Fresh confirmation sees only the problem and samples.\n'
         'Cancel a run; download the final JSON evidence.',
         'The model generates an independent testing module: parser, renderer, validator, brute force solver, generators and reducer. Preparation checks all samples and input round trips. Restricted Docker containers execute every submission and reference. The search tries tiny exhaustive, random and adversarial inputs. A fresh independent request checks an observed disagreement.'),
        ('Today\'s executed Gemini result',
         f"Input: {evidence['stdin'].strip()}\n"
         f"Expected: {evidence['expected'].strip()}\n"
         f"Submitted output: {evidence['actual']['stdout'].strip()}\n\n"
         'Both sample-checked references agree.\n'
         'Both input validators accept the retained input.\n'
         f"Elapsed: {result['elapsed']:.1f} seconds | Seed: {result['seed']}\n"
         'Complete evidence: submission/evidence-day2-gemini.json',
         f"Today's real Gemini run retained zero and negative one. The reference answer is negative one, while the submitted program prints positive one. Both sample checked references and both input validators agreed. The run finished in {result['elapsed']:.0f} seconds. The repository preserves its input, outputs, reference implementations, source hashes and counts."),
        ('Inside the corroboration gate',
         f'app/search.py, line {line+1}\n\n'
         'Actual source excerpt:\n\n' + excerpt + '\n\n'
         'Either failed check keeps the finding unconfirmed.\n'
         'Reduction rechecks every accepted smaller input.',
         'Here is the actual corroboration gate in the search engine. Both validators and both reference outputs must agree. If either check fails, this branch returns an unconfirmed disagreement. Reduction then accepts only smaller valid inputs that still fail after fresh executions. No generated or submitted code is executed on the host.'),
        ('Measured coverage and honest limits',
         'Gemini benchmark: 3/5 wrong controls corroborated.\n'
         'Zero false corroborated correct-control findings.\n'
         'Three correct controls inconclusive; two provider failures.\n'
         'All 64 attempts retained, including failures.\n\n'
         'Inconclusive is not a correctness claim.\n'
         'AI references can share mistakes; no proof or global minimality.\n'
         'Source and local setup: github.com/And850/counterexample-lab',
         'The complete Gemini benchmark corroborated three of five wrong controls, with zero false corroborated correct control findings. Three correct controls were inconclusive; two had provider failures. All sixty four attempts remain visible. This is evidence, not proof or a globally minimal case. The public repository provides local setup instructions. The current scope is C plus plus seventeen with unique integer outputs.'),
    ]
    font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
    captions = []
    timings = []
    for index, (title, body, narration) in enumerate(slides):
        speech = root / f'{index}.txt'
        speech.write_text(narration)
        audio = root / f'{index}.aiff'
        subprocess.run(['say', '-v', 'Samantha', '-r', '175', '-f', str(speech), '-o', str(audio)], check=True)
        seconds = max(20, duration(audio) + 1.5)
        timings.append(seconds)
        frame = Image.new('RGB', (1280, 720), '#101319')
        draw = ImageDraw.Draw(frame)
        draw.rectangle((80, 76, 160, 82), fill='#a4e4c5')
        title_font = ImageFont.truetype(font_path, 44)
        assert draw.textbbox((0, 0), title, font=title_font)[2] <= 1120
        draw.text((80, 120), title, fill='#e9edf5', font=title_font)
        body_font = ImageFont.truetype(font_path, 21 if index == 4 else 27)
        wrapped = '\n'.join(textwrap.fill(s, width=100 if index == 4 else 76) if s else '' for s in body.splitlines())
        box = draw.multiline_textbbox((80, 230), wrapped, font=body_font, spacing=12)
        assert box[2] <= 1200 and box[3] < 625, (index, box)
        draw.multiline_text((80, 230), wrapped, fill='#c4cbd8', font=body_font, spacing=12)
        draw.text((80, 650), f'{index+1}/6 | Recorded evidence | Synthesized narration',
                  fill='#a2aabb', font=ImageFont.truetype(font_path, 17))
        png = root / f'{index}.png'
        frame.save(png)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
            '-loop', '1', '-i', str(png), '-i', str(audio), '-r', '10', '-t', str(seconds),
            '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
            '-af', 'apad', '-c:a', 'aac', '-ar', '48000', '-ac', '2', str(root / f'{index}.mp4')], check=True)
        captions.append(f'## Slide {index+1}: {title}\n\n{narration}\n')
    playlist = root / 'concat.txt'
    playlist.write_text('\n'.join(f"file '{i}.mp4'" for i in range(len(slides))))
    output = Path('submission/narrated-evidence-walkthrough.mp4')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat',
        '-safe', '0', '-i', str(playlist), '-c', 'copy', '-movflags', '+faststart', str(output)], check=True)
    assert 120 <= duration(output) <= 180
    Path('submission/narrated-video-script.md').write_text(
        '# Narrated evidence walkthrough\n\nRecorded evidence and actual source, with synthesized macOS narration. '
        'This is not a browser recording.\n\n' + '\n'.join(captions))
    print(f'Created {output}: {duration(output):.2f} seconds, six narrated slides.')


if __name__ == '__main__':
    main()

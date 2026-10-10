"""Render a silent evidence walkthrough from a real corroborated run, not a UI recording."""
import json
from pathlib import Path
import subprocess
import textwrap
from PIL import Image, ImageDraw, ImageFont


def main():
 result=json.loads(Path('.runs/live-smoke-result.json').read_text())
 assert result['outcome']=='corroborated_counterexample'
 e=result['evidence'];assert e['references_agree'] and e['validators_agree']
 root=Path('.runs/demo');root.mkdir(parents=True,exist_ok=True)
 font='/System/Library/Fonts/Supplemental/Arial.ttf'
 slides=[
 ('Find the input that breaks it','Counterexample Lab\nAI for Automation | EvoHacks\n\nA local browser workflow for C++17.\n\nTurn the counterexample search into an executed, inspectable result.'),
 ('Samples can pass a wrong algorithm','Problem: sum two integers in [-100, 100].\nSample: 2 3 -> 5\n\nSubmitted bug:\nstd::cout << std::abs(a + b);\n\nPaste text or import saved Codeforces HTML.\nPaste code or upload a .cpp file.'),
 ('Generate. Execute. Check.','AI writes an independent small-case module.\n\nCheck all samples and input round trips.\nSearch tiny exhaustive, random and boundary cases.\n\nRestricted Docker executes every reference and submission.\nA fresh second request sees only problem and samples.'),
 ('A real corroborated disagreement',f"Input: {e['stdin'].strip()}\nReference output: {e['expected'].strip()}\nSubmitted output: {e['actual']['stdout'].strip()}\n\nBoth sample-checked references agree.\nBoth input validators accept the case.\nRun time: {result['elapsed']:.1f} seconds | Seed: {result['seed']}"),
 ('Evidence you can inspect','Download the complete result as JSON.\n\nInput, actual output and expected output.\nPrimary and independent reference implementations.\nSource hashes, seed and test counts.\n\nReduction re-executes every accepted smaller case.\nNo claim of global minimality.'),
 ('Useful evidence. Honest limits.','No disagreement within the budget is inconclusive.\nAI references can share a mistake.\nSmall cases may miss large-input bugs.\n\nLocal Qwen3.5-9B | No paid API required\nSource: github.com/And850/counterexample-lab\n\nEvidence walkthrough; not a browser recording.')]
 for index,(title,body) in enumerate(slides):
  titlefile=root/f'{index}-title.txt';bodyfile=root/f'{index}-body.txt';footerfile=root/f'{index}-footer.txt'
  titlefile.write_text(title);bodyfile.write_text('\n'.join(textwrap.fill(line,width=76) if line else '' for line in body.splitlines()));footerfile.write_text(f'{index+1} / 6   |   Counterexample Lab   |   Real local execution')
  image=Image.new('RGB',(1280,720),'#101319');draw=ImageDraw.Draw(image)
  draw.rectangle((80,76,160,82),fill='#a4e4c5')
  draw.text((80,120),title,fill='#e9edf5',font=ImageFont.truetype(font,48))
  draw.multiline_text((80,230),bodyfile.read_text(),fill='#c4cbd8',font=ImageFont.truetype(font,27),spacing=14)
  draw.text((80,650),footerfile.read_text(),fill='#a2aabb',font=ImageFont.truetype(font,17))
  frame=root/f'{index}.png';image.save(frame)
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-i',str(frame),'-r','10','-t','20','-c:v','libx264','-threads','2','-preset','veryfast','-pix_fmt','yuv420p',str(root/f'{index}.mp4')],check=True)
 playlist=root/'concat.txt';playlist.write_text('\n'.join(f"file '{index}.mp4'" for index in range(6)))
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(playlist),'-c','copy','-movflags','+faststart','submission/evidence-walkthrough.mp4'],check=True)
 print('Created submission/evidence-walkthrough.mp4 (120 seconds, silent evidence slides).')


if __name__=='__main__':main()

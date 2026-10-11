# EvoHacks submission checklist

Submit today, October 11, 2026, before **20:59 Europe/Madrid**, using the admin's stricter 11:59 AM PDT cutoff. The [Devpost overview](https://evohackathon2026.devpost.com/) displays 12:00 PM PDT (21:00 Madrid).

## Exact project fields

| Field | Value |
|---|---|
| Name | Counterexample Lab |
| Tagline | Find the input that breaks your C++ algorithm. |
| Description | Copy `submission/devpost-description.md`. |
| Source repository | https://github.com/And850/counterexample-lab |
| Try it out / setup | https://github.com/And850/counterexample-lab#run-locally |
| Built with | Python, FastAPI, Pydantic, Beautiful Soup, Docker, GNU C++17, Gemini, LM Studio, HTML, CSS, JavaScript |
| Team | Solo; And850 |
| Category/theme | AI for Automation |
| New project | Core implementation completed during the hackathon window; planning preceded kickoff. |

Localhost is only accessible on your machine; use the public README setup link for judges. Local setup instructions meet the overview's Access Link / Build requirement. A hosted execution service is not provided.

## Video ready for upload

File: `submission/narrated-evidence-walkthrough.mp4` (2:14.5, 1280×720, H.264/AAC, about 2.4 MB). This uses the built-in Mac voice, explicitly labeled synthesized narration. It shows recorded evidence, supported input/features, an actual source excerpt and measured limitations; it is not a browser recording.

The October 11 Gemini run in `submission/evidence-day2-gemini.json` was corroborated in 69.1 seconds. The full benchmark remains 64 fixed-control runs: 3/5 wrong controls corroborated in the complete Gemini round, zero false corroborated correct-control findings; three correct controls inconclusive and two provider failures.

Upload the MP4 to YouTube, Vimeo or Youku with link-accessible visibility, then paste its shareable URL into Devpost's video field. A local file or GitHub MP4 URL is not accepted by that field. See [Devpost's video upload instructions](https://help.devpost.com/article/85-uploading-a-demo-video).

## Remaining actions

- [ ] Open the app at `http://127.0.0.1:8002` in your own browser. Check paste/HTML import, C++ upload, progress/cancellation and JSON download; backend and offline DOM checks already passed.
- [ ] Watch the narrated video and confirm it represents your project accurately.
- [ ] Upload the video and obtain its supported-host URL.
- [ ] Sign in to the hackathon on Devpost and enter the fields above.
- [ ] Review the final submission, accept the applicable terms yourself, submit before 20:59 Madrid and verify its submitted status.

The agent's browser tool rejected access to both the local app and Devpost because permission was declined. Broader filesystem permissions did not grant browser access. No alternative browser, cookie-based request or indirect submission workaround was attempted, and no Devpost submission has been made.

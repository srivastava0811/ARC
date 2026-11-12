# Submission checklist

- [x] Set the README clone URL to `https://github.com/srivastava0811/ARC.git`.
- [x] Push the reviewed source and make the repository public before submission.
- [ ] Review files selected for publication: no `.env`, buyer passwords, logs,
  virtual environments, dependencies, or build output. Include `.env.example` files.
- [ ] Scan the final repository and **all Git history** for secrets before making
  it public. Rotate any credential that was committed, even after deleting it.
- [ ] Confirm GitHub detects the MIT LICENSE.
- [ ] Follow the README from a fresh clone, without private local state. Test
  Docker readiness, dependency installs, migrations, and both startup commands.
- [ ] Exercise monitors, keyboards, mice, clarification, and evidence/tradeoffs.
- [ ] Check Gemini model access/quota and Channel3 access for judging credentials.
- [ ] Complete actual Sandbox buyer approval and return to a captured-payment
  receipt. Mocked tests do not replace this check.
- [ ] Ensure judges have integration access: their own accounts or dedicated test
  credentials supplied through an organizer-approved private channel. Never
  publish API keys or buyer passwords in the repository.
- [ ] Check the video and submission fields against the
  [official rules](https://paypalaihackathon.devpost.com/rules).

Show the request, four stages, evidence, explicit approval, Sandbox checkout,
payment processing, and saved receipt. State whether the catalog is synthetic or
live and whether Gemini is enabled. Leave servers running during the demonstration.

Remaining checks: review any subsequent commits for secrets and verify final-clone
reproduction. Docker is unavailable on the audit machine, so its
runtime check remains pending. Complete integration judging requires valid
credentials and sufficient quota. See [validation notes](VALIDATION.md).

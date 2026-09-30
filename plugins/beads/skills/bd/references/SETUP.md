# Installing bd

Ask the user before installing anything. State which command you intend to
run and wait for a yes. Do not install on silence.

Install instructions live in the beads README:
https://github.com/gastownhall/beads#-installation

Options listed there:

- `curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh | bash`
- `brew install beads`
- `npm install -g @beads/bd`

After installing, confirm the binary is on `PATH`:

```bash
bd version
```

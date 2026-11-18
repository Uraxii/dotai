---
description: 'Set the OX VibeSec API token (explains the terminal route; never reads a token from the chat)'
---

If the user typed anything after the command, do not run anything. Tell the user that OX never reads a token from the chat.

In every case, reply with the two ways to set the token, as plain text the user can copy:

1. Run the OX installer again with --token. See https://docs.ox.security/vibesec/installing-vibesec.
2. Put the token in an environment variable, then run this command in a terminal:

   "<plugin dir>/hooks/ox" --api-key "$OX_TOKEN"

   The plugin dir is the path of the installed plugin. The command `claude plugin list` shows it.

Keep the reply short. Do not run any command.

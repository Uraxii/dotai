// Reminds opencode to load poteto-mode, the same way session_start_context.py
// does for Claude Code, Codex, and Copilot CLI.
//
// opencode has no hook that fires once at session start and can inject
// context: `session.created` only notifies, fire-and-forget
// (anomalyco/opencode@228e9095, packages/opencode/src/plugin/index.ts:259).
// The one hook that can push text onto the model's context is
// `experimental.chat.system.transform`, which runs before every LLM request
// (packages/plugin/src/index.ts:291-296, call site
// session/llm/request.ts:69-73). This plugin uses that hook: it shells out to
// session_start_context.py once, at plugin load, and caches the reminder
// text so every request after that is a plain array push with no process
// spawn.
//
// Install: symlink this file into ~/.config/opencode/plugin/ (a copy would
// break the sibling lookup below), or point opencode.json's "plugin" array
// at its path. See README.md.
import type { Plugin } from "@opencode-ai/plugin"

export const PotetoModeReminder: Plugin = async ({ $ }) => {
	const scriptPath = new URL("session_start_context.py", import.meta.url).pathname
	let reminder = ""
	try {
		reminder = (await $`python3 ${scriptPath} --harness opencode`.text()).trim()
	} catch {
		reminder = ""
	}

	return {
		"experimental.chat.system.transform": async (_input, output) => {
			if (reminder) output.system.push(reminder)
		},
	}
}

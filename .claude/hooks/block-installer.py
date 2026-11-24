"""Block a shell command that would run install-macos.sh.

Claude Code runs this before each Bash command. The installer moves
/Applications/Anki.app to the Trash, so only a person should run it.
Commands that only name the file (shellcheck, bash -n, git diff, cat)
are allowed.

The command counts as running the installer if one of its parts:
  - starts with the script (./install-macos.sh, path/install-macos.sh),
    also after sudo, env, exec, nohup and similar commands;
  - gives the script to a shell or to source (bash install-macos.sh,
    sh -x install-macos.sh, . ./install-macos.sh, bash < install-macos.sh);
  - runs it through "bash -c" or "sh -c";
  - is a shell that reads its input, in a command that names the script
    (cat install-macos.sh | bash).
"bash -n" and "sh -n" only check the syntax, so they are allowed.

Exit code 2 blocks the command and shows the message to Claude.
"""

import json
import os
import shlex
import sys

NAME = "install-macos.sh"
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish", "source", "."}
# Commands that run the command after them.
WRAPPERS = {"sudo", "env", "exec", "nohup", "command", "nice", "time",
            "caffeinate", "xargs", "builtin", "!", "{", "then", "do",
            "else", "if", "while", "until"}
# Options of a wrapper that take a value (sudo -u root, nice -n 5).
VALUE_OPTIONS = {"-u", "-g", "-U", "-C", "-h", "-p", "-n", "-D", "-r", "-t"}
SEPARATORS = set(";&|()`")


def is_script(word):
    return os.path.basename(word) == NAME


def parts(command):
    """Split a command into its simple commands, as lists of words."""
    lexer = shlex.shlex(command.replace("\n", ";"), posix=True,
                        punctuation_chars=";&|()<>`")
    lexer.whitespace_split = True
    part = []
    for token in lexer:
        if set(token) <= SEPARATORS:
            if part:
                yield part
            part = []
        else:
            part.append(token)
    if part:
        yield part


def runs_installer(command):
    try:
        all_parts = list(parts(command))
    except ValueError:
        # The command could not be read (for example an open quote).
        # Block it if it names the script at all.
        return NAME in command
    for words in all_parts:
        words = list(words)
        # Skip variable settings and wrappers with their options.
        while words:
            w = words[0]
            if "=" in w and not w.startswith("-"):
                words.pop(0)
            elif w in WRAPPERS or os.path.basename(w) in WRAPPERS:
                words.pop(0)
                while words and words[0].startswith("-"):
                    if words.pop(0) in VALUE_OPTIONS and words:
                        words.pop(0)
            else:
                break
        if not words:
            continue
        first = words[0]
        if is_script(first):
            return True
        if os.path.basename(first) not in SHELLS:
            continue
        args = words[1:]
        options = [a for a in args if a.startswith("-") and a != "-"]
        if any(o.startswith("-") and not o.startswith("--") and "n" in o[1:]
               for o in options):
            continue  # Syntax check only.
        if "-c" in options or any(o.startswith("-") and "c" in o[1:]
                                  and not o.startswith("--") for o in options):
            rest = [a for a in args if not a.startswith("-")]
            if rest and runs_installer(rest[0]):
                return True
            continue
        if "<" in args:
            i = args.index("<")
            if i + 1 < len(args) and is_script(args[i + 1]):
                return True
        script = [a for a in args if not a.startswith("-") and a not in "<>"]
        # "-s" makes the shell read its input; the other words are arguments.
        reads_input = not script or any(
            o.startswith("-") and not o.startswith("--") and "s" in o[1:]
            for o in options)
        if reads_input:
            if NAME in command:
                return True  # As in "cat install-macos.sh | bash".
            continue
        if is_script(script[0]):
            return True
    return False


def main():
    try:
        command = json.load(sys.stdin)["tool_input"]["command"]
    except (ValueError, KeyError, TypeError):
        print("Blocked: the hook could not read the command.", file=sys.stderr)
        return 2
    if runs_installer(command):
        print(f"Blocked: this command would run {NAME}. That script moves "
              "/Applications/Anki.app to the Trash. Run it yourself in a "
              "terminal if you mean to.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
  - runs it through "bash -c", "sh -c", "bash -lc" or inside "$(...)";
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
VALUE_OPTIONS = {"-u", "-g", "-U", "-C", "-h", "-p", "-n", "-D", "-r", "-t", "-I", "-L", "-P", "-d", "-S", "--split-string"}
SHELL_VALUE_OPTIONS = {"-o", "+o", "--rcfile", "--init-file"}
PIPELINE_BREAKS = set(";&()`")
SEPARATORS = set(";&|()`")
MAX_DEPTH = 8


def is_script(word):
    return os.path.basename(word) == NAME


def pipelines(command):
    """Split a command into pipelines, each a list of simple-command word lists."""
    lexer = shlex.shlex(command.replace("\n", ";"), posix=True,
                        punctuation_chars=";&|()<>`")
    lexer.whitespace_split = True
    pipe, part = [], []
    for token in lexer:
        if token == "|":
            if part:
                pipe.append(part)
                part = []
        elif set(token) <= SEPARATORS:
            if part:
                pipe.append(part)
                part = []
            if pipe:
                yield pipe
                pipe = []
        else:
            part.append(token)
    if part:
        pipe.append(part)
    if pipe:
        yield pipe


def parse_shell_args(args):
    """Split shell arguments into (options_before_target, remaining_operands, redir_input)."""
    options = []
    operands = []
    redir_input = []
    i = 0
    in_options = True
    while i < len(args):
        a = args[i]
        if a in ("<", "<<", "<<<") and i + 1 < len(args):
            if a == "<":
                redir_input.append(args[i + 1])
            i += 2
            continue
        if a in (">", ">>", "<>", ">&", "<&") and i + 1 < len(args):
            i += 2
            continue
        if a.isdigit() and i + 1 < len(args) and args[i + 1] in (">", ">>", "<", ">&", "<&"):
            if args[i + 1] == "<" and i + 2 < len(args):
                redir_input.append(args[i + 2])
            i += 3
            continue
        if a in ("<", ">"):
            i += 1
            continue
        if in_options:
            if a == "--":
                in_options = False
                i += 1
                continue
            if a in SHELL_VALUE_OPTIONS:
                options.append(a)
                i += 2
                continue
            if (a.startswith("-") or a.startswith("+")) and a not in ("-", "+"):
                options.append(a)
                i += 1
                continue
            in_options = False
        operands.append(a)
        i += 1
    return options, operands, redir_input


def has_short_flag(options, flag):
    return any(
        o.startswith("-") and not o.startswith("--") and flag in o[1:]
        for o in options
    )


def runs_installer(command, depth=0):
    if depth > MAX_DEPTH:
        return NAME in command
    try:
        all_pipes = list(pipelines(command))
    except ValueError:
        # The command could not be read (for example an open quote).
        # Block it if it names the script at all.
        return NAME in command
    for pipe in all_pipes:
        pipe_text = " ".join(w for cmd in pipe for w in cmd)
        for words in pipe:
            words = list(words)
            # Check command substitutions inside double-quoted tokens.
            for token in words:
                if "$(" in token or "`" in token:
                    inner = token.replace("$(", " ; ").replace("`", " ; ")
                    if runs_installer(inner, depth + 1):
                        return True
            # Skip variable settings and wrappers with their options.
            while words:
                w = words[0]
                if "=" in w and not w.startswith("-"):
                    words.pop(0)
                elif w in WRAPPERS or os.path.basename(w) in WRAPPERS:
                    words.pop(0)
                    while words and words[0].startswith("-"):
                        opt = words.pop(0)
                        if opt in VALUE_OPTIONS and words:
                            val = words.pop(0)
                            if opt in ("-S", "--split-string") and runs_installer(val, depth + 1):
                                return True
                else:
                    break
            if not words:
                continue
            first = words[0]
            if is_script(first):
                return True
            if os.path.basename(first) == "eval":
                if runs_installer(" ".join(words[1:]), depth + 1):
                    return True
                continue
            if os.path.basename(first) not in SHELLS:
                continue
            options, operands, redir_input = parse_shell_args(words[1:])
            if has_short_flag(options, "n"):
                continue  # Syntax check only (option appeared before the script).
            if has_short_flag(options, "c"):
                if operands and runs_installer(operands[0], depth + 1):
                    return True
                continue
            if any(is_script(target) for target in redir_input):
                return True
            # "-s" makes the shell read its input; only block if this pipeline names the script.
            reads_input = not operands or has_short_flag(options, "s")
            if reads_input:
                if NAME in pipe_text:
                    return True  # As in "cat install-macos.sh | bash".
                continue
            if is_script(operands[0]):
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

"""Custom language definitions for DevOps language-aware chunking.

Defines CustomLanguageSpec instances for HCL (Terraform), Dockerfile, and
Bash/Shell files. These specs tell CocoIndex's SplitRecursively how to chunk
DevOps files at structurally meaningful boundaries instead of plain-text splits.

All separator patterns use standard Rust regex syntax only (no lookaheads,
lookbehinds, or backreferences). CocoIndex uses the standard Rust `regex`
crate v1.12.2. See: https://docs.rs/regex/latest/regex/#syntax
"""

import cocoindex

HCL_LANGUAGE = cocoindex.functions.CustomLanguageSpec(
    language_name="hcl",
    separators_regex=[
        # Level 1: Top-level HCL block boundaries (12 keywords)
        r"\n(?:resource|data|variable|output|locals|module|provider|terraform|import|moved|removed|check) ",
        # Level 2: Blank lines between sections
        r"\n\n+",
        # Level 3: Single newlines
        r"\n",
        # Level 4: Whitespace (last resort)
        r" ",
    ],
    aliases=["tf", "tfvars"],
)

DOCKERFILE_LANGUAGE = cocoindex.functions.CustomLanguageSpec(
    language_name="dockerfile",
    separators_regex=[
        # Level 1: FROM (build stage boundaries -- highest priority)
        r"\nFROM ",
        # Level 2: Major instructions (case-sensitive, Dockerfile convention)
        r"\n(?:RUN|COPY|ADD|ENV|EXPOSE|VOLUME|WORKDIR|USER|LABEL|ARG|ENTRYPOINT|CMD|HEALTHCHECK|SHELL|ONBUILD|STOPSIGNAL|MAINTAINER) ",
        # Level 3: Blank lines
        r"\n\n+",
        # Level 4: Comment lines
        r"\n# ",
        # Level 5: Single newlines
        r"\n",
        # Level 6: Whitespace (last resort)
        r" ",
    ],
    aliases=[],
)

BASH_LANGUAGE = cocoindex.functions.CustomLanguageSpec(
    language_name="bash",
    separators_regex=[
        # Level 1: Function keyword definitions
        r"\nfunction ",
        # Level 2: Blank lines (logical section separators in scripts)
        r"\n\n+",
        # Level 3: Comment-based section headers
        r"\n#+",
        # Level 4: Control flow keywords
        r"\n(?:if |for |while |case |until )",
        # Level 5: Single newlines
        r"\n",
        # Level 6: Whitespace (last resort)
        r" ",
    ],
    aliases=["sh", "zsh", "shell"],
)

DEVOPS_CUSTOM_LANGUAGES: list[cocoindex.functions.CustomLanguageSpec] = [
    HCL_LANGUAGE,
    DOCKERFILE_LANGUAGE,
    BASH_LANGUAGE,
]

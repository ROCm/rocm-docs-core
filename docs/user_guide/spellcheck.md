---
myst:
    html_meta:
        "description": "Rocm docs core has spell checks run on every pull request"
        "keywords": "Spell check in ROCm documentation, Spell check in ROCm docs core, ROCm docs core user guide"
---

# Spell Check

`rocm-docs-core` has spell checks run on every pull request (PR) via GitHub Actions.

If a PR fails spell check, the errors must be addressed before it can be merged.

The results of a spell check is viewable in the "Checks" tab for a PR.

## Types of Errors

### Spelling Mistake

View the "Details" for a spell check and fix the misspelled words.

### New words or Acronyms

Spell check may flag errors if it does not recognize a word.

The reason could be that the word is not familiar to the dictionary used
or an unfamiliar acronym.

To get spell check to recognize this word, add it to the `.wordlist.txt` file,
located at the root of the project (for this project, `rocm-docs-core`,
that would be the `rocm-docs-core` folder).

### Special keywords

If the word is not meant to be a dictionary word, but is still valid
technical terminology, wrap the word with the backtick (`) key.

#### Keyword examples

- File or folder names
- Commands or arguments
- Code blocks
- Names of executables or binaries

## More Information

For more information, see the GitHub Action
[spellcheck-github-actions](https://github.com/rojopolis/spellcheck-github-actions)

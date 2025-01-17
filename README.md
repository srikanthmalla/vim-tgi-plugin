# vim_tgi_plugin

A Vim plugin to interact with LLMs for inline edits and chat.

## Installation

choose one of the following two options:

### using [vim-plug](https://github.com/junegunn/vim-plug): 

`Plug 'srikanthmalla/vim-tgi-plugin'`

**NOTE**: update <url> and port in `API_URL="http://<url>:8080/v1/chat/completions"` in `.vim/plugged/vim-tgi-plugin/python/config.py` 

### clone the repo and manually add the path to runtime:

Copy this repo under `.vim` and add this below line to `.vimrc`

```
set runtimepath+=~/.vim/vim-tgi-plugin
```

**NOTE**: update <url> and port in `API_URL="http://<url>:8080/v1/chat/completions"` in `vim-tgi-plugin/python/config.py` 

## Dependencies:

[`fzf.vim`](https://github.com/junegunn/fzf.vim) for interactive selection of files/ctags

`sudo apt install universal-ctags` to generate tags to functions and classes for easy finding them with fzf

---

## Commands

### `:InlineEdit <args>` or `:'<,'>InlineEdit <args>`
- Sends the selected range or current buffer to the LLM.
- If `@file` is provided, the current file content or the specified file (tab after @file) content will be included in the prompt.
- If `@tag` is provided, the ctag content (tab after @tag) is shown to select and will  be included in the prompt.
- If `@buf` is provided, you can select vim buffer that is standard or terminal.

### `:StartChat <args>`
- Opens a split window for chatting with the LLM.

### `:StopChat`
- Stops the ongoing chat interaction.

---

## Keybindings

| Keybinding    | Command            |
|---------------|--------------------|
| `<Leader>ie`  | `:InlineEdit <args text>` , `:[range] InlineEdit  <args text>`      |
| `<Leader>a`   | `:AcceptSuggestion`  |
| `<Leader>gt`  | `:call GenerateCtags()`     |
| `<Leader>sc`  | `:StartChat <args text>`        |
| `<Leader>ss`  | `:StopChat`          |

---

## Example Usage

1. **Send Current File to LLM**:
    ```vim
    :InlineEdit write sum function in python
    ```

need to to tab after @file or @tag or @buf to select other files or functions/classes or vim(terminal/standard) buffers respectively

2. **Chat Interaction**:
    ```vim
    :StartChat What is the difference between Vim and Neovim?
    ```

---

## Requirements

- Vim compiled with `+python3`.

---

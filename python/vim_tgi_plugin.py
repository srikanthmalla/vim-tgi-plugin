"""
Script: vim_tgi_plugin.py
Author: Srikanth Malla
Date: January 8, 2025
Description: Supporting functionalities of VIM TGI Plugin written in python to talk to TGI Huggingface.
"""

import vim
import requests
import json
import time
from threading import Thread
from config import API_URL

# TGI Endpoint Configuration
HEADERS = {"Content-Type": "application/json"}
PARAMETERS = {
    "model": "tgi",
    "stream": True,
    "max_tokens": 8192,
}

# Control flag to stop generation
STOP_GENERATION = False

# Tracks lines with markdown syntax for removal later
LINES_TO_REMOVE = []
# Global variable to store the last selected range
LAST_SELECTED_RANGE = None

def stream_response_chat(messages):
    """
    Streams chat completion token by token based on user messages.

    Parameters:
    - messages (list): The list of messages to send to the assistant.

    Yields:
    - Each token in the generated response as it streams in.
    """
    payload = {
        "model": PARAMETERS["model"],
        "messages": messages,
        "stream": PARAMETERS["stream"],
        "max_tokens": PARAMETERS["max_tokens"],
    }

    try:
        with requests.post(API_URL, json=payload, headers=HEADERS, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if STOP_GENERATION:
                    break
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() and data != "[DONE]":
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue
    except requests.RequestException as e:
        vim.command(f"echo 'Request error: {e}'")

def inline_edit(args, start_line=None, end_line=None):
    """
    Inline edit by sending the user input or selected range to the LLM.

    Parameters:
    - args (str): User input for inline edit.
    - start_line (int): Start line of the selected range.
    - end_line (int): End line of the selected range.
    """
    global STOP_GENERATION, LINES_TO_REMOVE, LAST_SELECTED_RANGE
    STOP_GENERATION = False
    LINES_TO_REMOVE = []

    if not args.strip() and (start_line is None or end_line is None):
        vim.command("echo 'No input or range provided. Aborting.'")
        return

    # Get selected text
    selected_text = ""
    if start_line is not None and end_line is not None:
        selected_text = "\n".join(vim.current.buffer[start_line - 1:end_line])

    # Combine user input and selected text
    input_text = f"{args}\n\n{selected_text}" if selected_text else args

    # Prepare conversation messages
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant. Return only code with comments in the code."},
        {"role": "user", "content": input_text},
    ]

    # Add assistant response placeholder
    target_line = end_line+1 if end_line else len(vim.current.buffer)+1
    
    # Ensure the buffer has enough lines to accommodate the target line
    while target_line > len(vim.current.buffer):
        vim.current.buffer.append("")
    
    if start_line is not None and end_line is not None:
        LAST_SELECTED_RANGE = (start_line, end_line)

        # Move text below target_line down by one line for the selected range
        vim.current.buffer[target_line:len(vim.current.buffer)] = (
            [""] + vim.current.buffer[target_line:len(vim.current.buffer)]
        )

    else:
        # No range selected, append at the end of the buffer
        target_line = len(vim.current.buffer) + 1
        vim.current.buffer.append("")   
    
    def stream_thread():
        global LINES_TO_REMOVE
        current_line = target_line  # Start inserting at the target line
        for data in stream_response_chat(messages):
            if STOP_GENERATION:
                break
            try:
                token_text = data["choices"][0]["delta"].get("content", "")
                if token_text:
                    current_line = append_cleaned_token_to_vim(token_text, current_line)
                    vim.command("redraw")
                    time.sleep(0.05)
            except Exception as e:
                vim.command(f"echo 'Error processing token: {e}'")

        # After completion, remove any markdown syntax lines
        remove_markdown_syntax_lines()

    Thread(target=stream_thread).start()

def remove_last_selected_lines():
    """
    Remove lines based on the last selected range.
    """
    global LAST_SELECTED_RANGE
    if LAST_SELECTED_RANGE is None:
        vim.command("echo 'No previously selected range to remove.'")
        return

    start_line, end_line = LAST_SELECTED_RANGE
    try:
        for line_no in range(end_line, start_line - 1, -1):  # Reverse to avoid shifting
            if 0 <= line_no - 1 < len(vim.current.buffer):  # Line numbers are 1-based in Vim
                del vim.current.buffer[line_no - 1]

        vim.command("echo 'Previously selected lines removed successfully.'")
        vim.command("redraw")  # Refresh the Vim screen
        LAST_SELECTED_RANGE = None  # Reset the range after removal
    except Exception as e:
        vim.command(f"echo 'Error removing lines: {e}'")

def append_cleaned_token_to_vim(token, start_line):
    """
    Append a cleaned token to Vim buffer, ensuring proper formatting.

    Parameters:
    - token (str): The token text to append.
    - start_line (int): Line number where the insertion starts.

    Returns:
    - Updated line number after appending the token.
    """
    global LINES_TO_REMOVE

    # Split the token into lines
    lines = token.splitlines()

    # Ensure the buffer has enough lines to insert at `start_line`
    while start_line > len(vim.current.buffer):
        vim.current.buffer.append("")

    for i, line in enumerate(lines):
        if "```" in line:
            # Track the line number relative to the current buffer
            LINES_TO_REMOVE.append(start_line-1)

        if i == 0:
            # Modify the first line at `start_line`
            if vim.current.buffer[start_line - 1]:
                vim.current.buffer[start_line - 1] += line  # Append to the line
            else:
                vim.current.buffer[start_line - 1] = line  # Replace the line
        else:
            # Insert new lines
            vim.current.buffer.append(line, start_line)
            start_line += 1

    # Add a trailing newline for cleaner output
    if token.endswith("\n"):
        vim.current.buffer.append("", start_line)
        start_line += 1
    # Autoscroll to the current insertion point
    vim.command(f"normal! {start_line}zz")
    return start_line

def remove_markdown_syntax_lines():
    """
    Remove all lines containing markdown syntax (` ``` `) from the Vim buffer.
    """
    global LINES_TO_REMOVE
    LINES_TO_REMOVE = sorted(set(LINES_TO_REMOVE), reverse=True)  # Sort and reverse for safe deletion
    for line_no in LINES_TO_REMOVE:
        if 0 <= line_no < len(vim.current.buffer):
            del vim.current.buffer[line_no]
    LINES_TO_REMOVE = []
    vim.command("redraw")  # Explicitly refresh the Vim screen

def stop_inline_edit():
    """
    Stop inline editing or streaming response.
    """
    global STOP_GENERATION
    STOP_GENERATION = True
    remove_markdown_syntax_lines()  # Ensure markdown syntax lines are removed
    vim.command("echo 'Inline editing stopped.'")
def start_chat(args):
    """
    Open a split window and display a chat interaction with the LLM.

    Parameters:
    - args (str): User input for the chat.
    """
    global STOP_GENERATION
    STOP_GENERATION = False  # Reset the stop flag
    vim.command("echo 'Entering start_chat'")
    if not args.strip():
        vim.command("echo 'No input provided. Aborting.'")
        return

    # Save the current buffer and window
    original_buffer_id = vim.current.buffer.number

    # Create or switch to the Chat Window split
    create_or_switch_to_split("Chat Window")

    # Get the Chat Window's buffer ID
    chat_buffer_id = vim.current.buffer.number

    # Add the user input to the chat history
    vim.current.buffer.append(f"User: {args}")
    vim.current.buffer.append("Assistant: ")  # Add Assistant label
    vim.current.window.cursor = (len(vim.current.buffer), 0)

    # Prepare the conversation
    messages = [{"role": "system", "content": "You are a helpful assistant."}]

    # Add chat history
    for line in vim.buffers[chat_buffer_id]:
        if line.startswith("User: "):
            messages.append({"role": "user", "content": line[6:]})
        elif line.startswith("Assistant: "):
            messages.append({"role": "assistant", "content": line[11:]})

    messages.append({"role": "user", "content": args})

    def stream_thread():
        original_buffer = vim.current.buffer  # Save the original buffer
        target_buffer = vim.buffers[chat_buffer_id]  # Get the Chat Window buffer

        for data in stream_response_chat(messages):
            if STOP_GENERATION:
                break
            try:
                token_text = data["choices"][0]["delta"].get("content", "")
                if token_text:
                    # Switch to the Chat Window buffer
                    vim.current.buffer = target_buffer
                    append_token_to_vim(token_text)
                    vim.command("redraw!")
                    # Restore the original buffer
                    vim.current.buffer = original_buffer
                vim.command("redraw")
                time.sleep(0.05)
            except Exception as e:
                vim.command(f"echo 'Error processing token: {e}'")

    # Create and start the thread
    thread = Thread(target=stream_thread)
    thread.start()

    # Wait for the thread to finish (optional if you want blocking behavior)
    # thread.join()

def stop_chat():
    """
    Stop the chat interaction.
    """
    global STOP_GENERATION
    STOP_GENERATION = True
    remove_markdown_syntax_lines()  # Ensure markdown syntax lines are removed
    vim.command("echo 'Chat stopped.'")

def find_existing_buffer(title):
    """
    Find an existing buffer by title.

    Parameters:
    - title (str): The title of the buffer to search for.

    Returns:
    - bool: True if the buffer exists, False otherwise.
    """
    for buf in vim.buffers:
        if buf.name and title in buf.name:
            return True
    return False
def switch_to_buffer(title):
    """
    Switch to an existing buffer by title, ensuring no overwriting or force-switching unnecessarily.
    """
    for buf in vim.buffers:
        if buf.name and title in buf.name:
            # Debugging: Log the current and target buffer names
            vim.command(f"echo 'Current buffer: {vim.current.buffer.name}'")
            vim.command(f"echo 'Target buffer: {buf.name}'")
            
            if vim.current.buffer.name == buf.name:
                vim.command("echo 'Already in the target buffer.'")
                return  # Already in the desired buffer, no need to switch
            
            try:
                vim.command(f"b {buf.number}")  # Switch to the buffer
                vim.command("redraw!")  # Refresh screen after switching
                vim.command(f"echo 'Switched to buffer: {buf.name}'")
            except vim.error as e:
                vim.command(f"echo 'Error switching to buffer: {e}'")
            return
    vim.command(f"echo 'Buffer with title {title} not found.'")


def create_or_switch_to_split(title):
    """
    Create a split window or switch to an existing one.
    """
    vim.command("echo 'Entering create_or_switch_to_split'")
    if find_existing_buffer(title):
        vim.command(f"echo 'Switching to existing buffer: {title}'")
        switch_to_buffer(title)
    else:
        vim.command(f"echo 'Creating a new buffer: {title}'")
        vim.command("belowright split")  # Create a new split below
        vim.command("resize 10")  # Resize the split
        create_new_buffer(title)
    vim.command("redraw!")  # Refresh screen

def create_new_buffer(title):
    """
    Create a new Vim buffer for displaying streamed content.

    Parameters:
    - title (str): The title for the new buffer.
    """
    vim.command("enew")  # Open a new empty buffer
    vim.command(f"file {title}")  # Set the buffer name
    vim.command("setlocal buftype=nofile")  # Make the buffer temporary (not written to disk)
    vim.command("setlocal bufhidden=wipe")  # Automatically close the buffer when abandoned
    vim.command("setlocal noswapfile")  # Disable swapfile for the buffer

def append_token_to_vim(token):
    """
    Append a token to Vim buffer, splitting by newlines.

    Parameters:
    - token (str): The token text to append.
    """
    lines = token.split("\n")
    for i, line in enumerate(lines):
        if i == 0:
            vim.current.buffer[-1] += line
        else:
            vim.current.buffer.append(line)
    # Autoscroll to the current insertion point
    vim.command("normal! G")

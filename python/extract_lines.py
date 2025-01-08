"""
Script: extract_lines.py
Author: Srikanth Malla
Date: January 8, 2025
Description: This script extracts details about a specific tag from a tags file generated by ctags in a Git repository. It identifies the file and the corresponding content based on the provided tag name and line number. Purpose for both previewing and selecting the content to send to AI Model.
Usage: python3 extract_lines.py <@tag_name#line_number>
"""

import sys
import os
import subprocess

def get_git_root():
    """Find the Git root directory."""
    try:
        git_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL)
        return git_root.decode("utf-8").strip()
    except subprocess.CalledProcessError:
        return None
def extract_tag_details(tags_file, selected):
    """Extract tag details and retrieve content from the file."""
    try:
        # Split the selected entry into tag name and line number
        tag_name, line_number = selected.split("#")
        line_number = int(line_number)

        # Read the tags file and get the specific line
        with open(tags_file, "r") as f:
            lines = f.readlines()
            if 1 <= line_number <= len(lines):
                tag_line = lines[line_number - 1].strip()  # Line numbers are 1-based
            else:
                return f"Error: Line number {line_number} out of range."
        
        # Parse the tag line for details
        parts = tag_line.split("\t")
        if len(parts) < 4:
            return f"Error: Malformed tag line: {tag_line}"

        tag_name, relative_path, pattern, _type, *attributes = parts
        start_line = end_line = None

        # Extract start and end line from attributes
        for attr in attributes:
            if attr.startswith("line:"):
                start_line = int(attr.split(":")[1])
            elif attr.startswith("end:"):
                end_line = int(attr.split(":")[1])

        # Ensure the start line is present
        if start_line is None:
            return f"Error: Start line not found for tag: {tag_name}"

        # Use the Git root to resolve the full path
        git_root = get_git_root()
        if git_root is None:
            return "Error: Not inside a Git repository."
        file_path = os.path.join(git_root, relative_path)

        # Check if the file exists
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        # Read the content from the specified lines
        with open(file_path, "r") as code_file:
            file_lines = code_file.readlines()
            if end_line:
                content = "".join(file_lines[start_line - 1 : end_line])
            else:
                content = file_lines[start_line - 1].strip()

        # Return the details
        return f"Tag: {tag_name}\nFile: {file_path}\nContent:\n{content}"

    except Exception as e:
        return f"Error processing tag: {e}"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 extract_lines.py <@tag_name#line_number>")
        sys.exit(1)

    selected_entry = sys.argv[1]
    # Get the Git root directory
    git_root = get_git_root()
    if git_root is None:
        print("Error: Not inside a Git repository.")
        sys.exit(1)

    # Path to the tags file in the Git root
    tags_file_path = os.path.join(git_root, "tags")
    result = extract_tag_details(tags_file_path, selected_entry)
    print(result)
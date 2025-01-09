" Script: vim_tgi_plugin.vim
" Author: Srikanth Malla
" Date: January 8, 2025
" Description: Suggestions using fzf and keybinding for vim and calling the functions implemented in python

" Check if Python3 is available
if !has("python3")
    echo "vim has to be compiled with +python3 to run this plugin"
    finish
endif

" Avoid loading the plugin multiple times
if exists('g:vim_tgi_plugin_loaded')
    finish
endif
let g:vim_tgi_plugin_loaded = 1

" Set up Python path
let s:plugin_root_dir = fnamemodify(resolve(expand('<sfile>:p')), ':h')

python3 << EOF
import sys
from os.path import normpath, join
plugin_root_dir = vim.eval('s:plugin_root_dir')
python_root_dir = normpath(join(plugin_root_dir, '..', 'python'))
sys.path.insert(0, python_root_dir)
import vim_tgi_plugin
import extract_lines
EOF

" Standalone function to generate ctags
function! GenerateCtags()
  " Check if inside a Git repository
  if system('git rev-parse --is-inside-work-tree') =~ 'true'
    let l:git_root = trim(system('git rev-parse --show-toplevel'))
    let l:tags_file = l:git_root . '/tags'

    " Generate tags
    echom "Generating ctags for Git repository..."
    call system('ctags --fields=+ne -R -f ' . shellescape(l:tags_file) . ' ' . shellescape(l:git_root))
    echom "Ctags generated at: " . l:tags_file
    " Construct sed command to remove the absolute path
    let l:sed_command = 'sed -i "s#' . l:git_root . '/##g" ' . l:tags_file

    " Execute the sed command
    call system(l:sed_command)
    echom "Ctags generated with relative paths at: " . l:tags_file
  else
    let l:tags_file = './tags'

    " Generate tags
    echom "Generating ctags for the current directory..."
    call system('ctags --fields=+ne -R -f ' . shellescape(l:tags_file) . ' .')
    echom "Ctags generated at: " . l:tags_file
  endif
endfunction

function! InlineEditFileCompletion(A, L, P)
  " Debugging: Log the current argument
  echom "InlineEditFileCompletion triggered with argument: " . a:A
      
  " If the argument ends with @file
  if a:A =~# '@file$'
    echom "Detected @file as the last argument"

    " Fetch the list of files
    if system('git rev-parse --is-inside-work-tree') =~ 'true'
      " Fetch Git-tracked files
      let l:git_root = trim(system('git rev-parse --show-toplevel'))
      let l:files = split(system('git -C ' . shellescape(l:git_root) . ' ls-files'), '\n')
    else
      " Fetch all files recursively
      let l:files = globpath('.', '**', 0, 1)
      let l:git_root = '.'
    endif

    " Use fzf for interactive selection
    let l:selected = fzf#run({
          \ 'source': l:files,
          \ 'sink':   function('s:handle_fzf_result'),
          \ 'options': '--preview "cat ' . shellescape(l:git_root) . '/{}" --preview-window right:50%',
          \ })

    " Return the selected file(s) or default
    return l:selected
  endif
  " Handle @tag
  if a:A =~# '@tag$'
    echom "Detected @tag as the last argument"

    " Generate ctags if not already present
    if system('git rev-parse --is-inside-work-tree') =~ 'true'
      let l:git_root = trim(system('git rev-parse --show-toplevel'))
      let l:tags_file = l:git_root . '/tags'
    else
      let l:tags_file = './tags'
    endif

    " Generate ctags if the tags file does not exist
    if !filereadable(l:tags_file)
     call GenerateCtags()
    endif

    " Extract tag names (first column) from the tags file
	let l:tags_output = []
	let l:tags_file_lines = readfile(l:tags_file)
	for l:index in range(len(l:tags_file_lines))
	  let l:line = l:tags_file_lines[l:index]
	  if l:line =~# '^[^\t]\+\t'
	    let l:tag_name = "@" . matchstr(l:line, '^[^\t]\+')
	    " Append tag name with its line number in the tags file
	    call add(l:tags_output, l:tag_name . '#' . (l:index + 1))
	  endif
	endfor
	" Use tags_output directly as the source
	let l:selected_tag = fzf#run({
	      \ 'source': l:tags_output,
	      \ 'options': '--with-nth=1 --preview "python3 ' . s:plugin_root_dir . '/../python/extract_lines.py {1}" --preview-window=right:50%',
	      \ })

	" Return the modified tag
	return l:selected_tag
  endif  
  " Default case: No suggestions
  " echom "No match for @file or @tag context"      
  return []
endfunction

" Function to handle the result from fzf
function! s:handle_fzf_result(file)
  " Optionally log the selected file
  " echom "Selected file: " . a:file
  return a:file
endfunction

function! InlineEditHandler(args, line1, line2)
  " Split the arguments into a list
  let l:args_list = split(a:args)
  let l:processed_args = []
  let l:current_file_content = ""
  let l:current_file_name = expand('%:p') " Get the current file name with full path
     
  " Determine the Git root (if inside a Git repository)
  let l:git_root = ""
  if system('git rev-parse --is-inside-work-tree') =~ 'true'
    let l:git_root = trim(system('git rev-parse --show-toplevel'))
  endif
     
  " If no filename is associated, use a placeholder
  if l:current_file_name == ""
    let l:current_file_name = "Untitled Buffer"
  endif
     
  " Process each argument
  for l:arg in l:args_list
    if l:arg == "@file"
      " If it's @file without a filename, use the current buffer content
      let l:current_file_content = join(getline(1, '$'), "\n")
      " Escape newlines for py3eval
      let l:file_content_escaped = substitute(l:current_file_content, '\n', '\\n', 'g')
      let l:processed_args += ["File (" . l:current_file_name . "):\\n" . l:file_content_escaped]
    elseif filereadable(l:arg) || (l:git_root != "" && filereadable(l:git_root . '/' . l:arg))
      " If it's a file, either relative to the current directory or the Git root
      let l:full_path = filereadable(l:arg) ? l:arg : l:git_root . '/' . l:arg
      let l:file_content = join(readfile(l:full_path), "\n")
      " Escape newlines for py3eval
      let l:file_content_escaped = substitute(l:file_content, '\n', '\\n', 'g')
      let l:processed_args += ["File (" . l:full_path . "):\\n" . l:file_content_escaped]
    elseif l:arg =~# '^@' " Handle @tag arguments
      
      " Generate ctags if not already present
      if system('git rev-parse --is-inside-work-tree') =~ 'true'
        let l:git_root = trim(system('git rev-parse --show-toplevel'))
        let l:tags_file = l:git_root . '/tags'
      else
        let l:tags_file = './tags'
      endif
      " Use py3eval to process the tag via extract_lines
      let l:tag_content = py3eval('extract_lines.extract_tag_details("' . l:tags_file . '", "' . l:arg . '")')

       " Escape newlines and quotes for py3eval
      let l:tag_content_escaped = substitute(l:tag_content, '\n', '\\n', 'g')
      let l:tag_content_escaped = substitute(l:tag_content_escaped, "'", "\\'", 'g')

      " Add the tag content to the processed arguments
      let l:processed_args += ["Tag (" . l:arg . "):\\n" . l:tag_content_escaped]
    else
      " Otherwise, keep the argument as is
      let l:processed_args += [l:arg]
    endif
  endfor
     
  " Join the processed arguments back into a single string
  let l:final_args = join(l:processed_args, " ")
     
  " Call the Python function
  call py3eval("vim_tgi_plugin.inline_edit(" . string(l:final_args) . ", " . string(a:line1) . ", " . string(a:line2) . ")")
endfunction

" Commands
" InlineEdit command with range support
command! -range -nargs=+ -complete=customlist,InlineEditFileCompletion InlineEdit call InlineEditHandler(<q-args>, <line1>, <line2>)
" command! -range -nargs=+ -complete=customlist,InlineEditFileCompletion InlineEdit python3 vim_tgi_plugin.inline_edit(<q-args>, <line1>, <line2>)
" command! -range -nargs=+ InlineEdit python3 vim_tgi_plugin.inline_edit(<q-args>, <line1>, <line2>)
command! AcceptSuggestion python3 vim_tgi_plugin.remove_last_selected_lines()
command! -nargs=+ StartChat python3 vim_tgi_plugin.start_chat(<q-args>)
command! StopChat python3 vim_tgi_plugin.stop_chat()

" Keybindings
nnoremap <Leader>ie :InlineEdit<Space>
nnoremap <Leader>a :AcceptSuggestion<Space>
vnoremap <Leader>ie :InlineEdit<Space>
nnoremap <Leader>sc :StartChat<Space>
nnoremap <Leader>ss :StopChat<CR>
nnoremap <Leader>gt :call GenerateCtags()<CR>

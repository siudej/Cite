--Applescript

--Set selection to full lines
set linefeed to ASCII character 10
set delimiters to {linefeed, return}

tell application "TeXShop"
    set whole_document to (text of front document) as string
    -- move beginning of the selection
    set selection_offset to offset of selection of front document
    set selection_length to length of selection of front document
    repeat until (selection_offset = 0) or (character selection_offset of the whole_document is in delimiters)
        set selection_offset to selection_offset - 1
        set selection_length to selection_length + 1
    end repeat
    set offset of (selection of front document) to selection_offset
    -- move end of the selection
    try
        set next_character to character (selection_offset + selection_length + 1) of the whole_document
        repeat until (next_character is in delimiters)
            set selection_length to selection_length + 1
            try
                set next_character to character (selection_offset + selection_length + 1) of ¬
                    the whole_document
            on error
                exit repeat
            end try
        end repeat
    end try
    set length of selection of front document to selection_length
end tell
--Save sellection to file
on maketemp()
    return do shell script "mktemp -t cite"
end maketemp

to writefile(thefile, _text)
    set fileID to open for access thefile with write permission
    set eof fileID to 0
    write _text to fileID as «class utf8»
    close access fileID
end writefile

set temppath to maketemp()
tell application "TeXShop" to set sel to the content of the selection of the front document
writefile(POSIX file temppath, sel)

--Run Cite and get the results
tell application "TeXShop" to set selection of front document to ""
do shell script "/usr/local/bin/cite < " & quoted form of temppath
set res to result
set temp_length to length of res
tell application "TeXShop"
    set temp_offset to offset of selection of front document
    set offset of selection of front document to selection_offset
    set selection of front document to res
    set offset of selection of front document to (temp_offset + temp_length + 1)
end tell


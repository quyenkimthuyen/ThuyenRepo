# Update data/questions/english.jsonl and compile web-html/questions-data.js
$englishJsonlPath = "e:/ThuyenRepo/TuyenSinhLop10/data/questions/english.jsonl"
$lines = Get-Content -Path $englishJsonlPath -Encoding Utf8

function ConvertTo-Utf8Json($obj) {
    $json = ConvertTo-Json -InputObject $obj -Depth 10 -Compress
    $regex = [regex]'\\u([0-9a-fA-F]{4})'
    $utf8Json = $regex.Replace($json, {
        param($match)
        [char][int]("0x" + $match.Groups[1].Value)
    })
    return $utf8Json
}

function ConvertTo-Utf8JsonIndented($obj) {
    $json = ConvertTo-Json -InputObject $obj -Depth 10
    $regex = [regex]'\\u([0-9a-fA-F]{4})'
    $utf8Json = $regex.Replace($json, {
        param($match)
        [char][int]("0x" + $match.Groups[1].Value)
    })
    return $utf8Json
}

$updatedLines = for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    if ($line.Trim() -eq "") {
        ""
        continue
    }
    $obj = ConvertFrom-Json $line
    # Pronunciation questions are english-001 to english-050
    if ($obj.chuyenDe -eq "Pronunciation" -and $obj.monHoc -eq "TiengAnh") {
        $idNum = [int]($obj.id -replace "english-", "")
        $roundIndex = $idNum - 1
        $variant = $roundIndex % 5
        
        # Retrieve context from current deBai
        $context = "school life"
        if ($obj.deBai -match "Context:\s*([^.]+)") {
            $context = $Matches[1].Trim()
        }
        # Retrieve focus from current deBai
        $focus = "sound discrimination"
        if ($obj.deBai -match "Focus:\s*([^.]+)") {
            $focus = $Matches[1].Trim()
        }
        
        if ($variant -eq 0) {
            $obj.deBai = "[Pronunciation] Which word has the underlined part pronounced differently from that of the others? Context: $context. Focus: $focus."
            $obj.luaChon = @("want<u>ed</u>", "need<u>ed</u>", "walk<u>ed</u>", "visit<u>ed</u>")
            $obj.dapAn = "walk<u>ed</u>"
            $obj.loiGiai = "The ending -ed in 'walked' is pronounced /t/, while the others are /id/."
        } elseif ($variant -eq 1) {
            $obj.deBai = "[Pronunciation] Which word has the underlined part pronounced differently from that of the others? Context: $context. Focus: $focus."
            $obj.luaChon = @("book<u>s</u>", "lamp<u>s</u>", "pen<u>s</u>", "map<u>s</u>")
            $obj.dapAn = "pen<u>s</u>"
            $obj.loiGiai = "The final -s in 'pens' is /z/, while the others are /s/."
        } elseif ($variant -eq 2) {
            $obj.deBai = "[Pronunciation] Which word has the underlined part pronounced differently from that of the others? Context: $context. Focus: $focus."
            $obj.luaChon = @("stopp<u>ed</u>", "watch<u>ed</u>", "play<u>ed</u>", "miss<u>ed</u>")
            $obj.dapAn = "play<u>ed</u>"
            $obj.loiGiai = "The ending -ed in 'played' is /d/, while the others are /t/."
        } elseif ($variant -eq 3) {
            $obj.deBai = "[Pronunciation] Which word has the underlined part pronounced differently from that of the others? Context: $context. Focus: $focus."
            $obj.luaChon = @("ma<u>ch</u>ine", "<u>ch</u>air", "tea<u>ch</u>er", "<u>ch</u>ildren")
            $obj.dapAn = "ma<u>ch</u>ine"
            $obj.loiGiai = "'ch' in machine is pronounced /ʃ/, not /tʃ/."
        } elseif ($variant -eq 4) {
            $obj.deBai = "[Pronunciation] Which word has the underlined part pronounced differently from that of the others? Context: $context. Focus: $focus."
            $obj.luaChon = @("<u>c</u>ity", "<u>c</u>ountry", "<u>c</u>enter", "<u>c</u>inema")
            $obj.dapAn = "<u>c</u>ountry"
            $obj.loiGiai = "The letter c in country is /k/, while the others are /s/."
        }
    }
    ConvertTo-Utf8Json $obj
}
# Write back english.jsonl
$updatedContent = ($updatedLines -join "`n") + "`n"
[System.IO.File]::WriteAllText($englishJsonlPath, $updatedContent, [System.Text.Encoding]::UTF8)

# Rebuild web-html/questions-data.js
$allRows = @()
foreach ($filename in @("math.jsonl", "literature.jsonl", "english.jsonl")) {
    $filePath = "e:/ThuyenRepo/TuyenSinhLop10/data/questions/$filename"
    $fileLines = Get-Content -Path $filePath -Encoding Utf8
    foreach ($line in $fileLines) {
        if ($line.Trim() -ne "") {
            $allRows += ConvertFrom-Json $line
        }
    }
}
$jsonString = ConvertTo-Utf8JsonIndented $allRows
$questionsDataPath = "e:/ThuyenRepo/TuyenSinhLop10/web-html/questions-data.js"
$jsContent = "window.QUESTION_BANK = " + $jsonString + ";`n"
[System.IO.File]::WriteAllText($questionsDataPath, $jsContent, [System.Text.Encoding]::UTF8)


# Now update data/real-exams/index.json and web-html/real-exam-detail-data.js with replacements
$filesToReplace = @(
    "e:/ThuyenRepo/TuyenSinhLop10/data/real-exams/index.json",
    "e:/ThuyenRepo/TuyenSinhLop10/web-html/real-exam-detail-data.js"
)

foreach ($filePath in $filesToReplace) {
    $content = [System.IO.File]::ReadAllText($filePath, [System.Text.Encoding]::UTF8)
    
    # 2026 Q1 prompt
    $content = $content.Replace(
        '"prompt": "1. Which word has the underlined part pronounced differently from that of the others.\n\nA. avoided\nB. frightened\nC. attended\nD. suggested"',
        '"prompt": "1. Which word has the underlined part pronounced differently from that of the others.\n\nA. avoid<u>ed</u>\nB. frighten<u>ed</u>\nC. attend<u>ed</u>\nD. suggest<u>ed</u>"'
    )
    # 2026 Q2 prompt
    $content = $content.Replace(
        '"prompt": "2. Which word has the underlined part pronounced differently from that of the others.\n\nA. chemist\nB. sensor\nC. pencil\nD. device"',
        '"prompt": "2. Which word has the underlined part pronounced differently from that of the others.\n\nA. <u>ch</u>emist\nB. <u>s</u>ensor\nC. pen<u>c</u>il\nD. devi<u>c</u>e"'
    )
    # 2026 Q1 answer
    $content = $content.Replace(
        '"answer": "B. frightened",',
        '"answer": "B. frighten<u>ed</u>",'
    )
    # 2026 Q2 answer
    $content = $content.Replace(
        '"answer": "D. device",',
        '"answer": "D. devi<u>c</u>e",'
    )
    
    # 2025 Q1 prompt
    $content = $content.Replace(
        '"prompt": "1. Which word has the underlined part pronounced differently from that of the others?\n\nA. delayed\nB. frightened\nC. remembered\nD. attacked"',
        '"prompt": "1. Which word has the underlined part pronounced differently from that of the others?\n\nA. delay<u>ed</u>\nB. frighten<u>ed</u>\nC. remember<u>ed</u>\nD. attack<u>ed</u>"'
    )
    # 2025 Q2 prompt
    $content = $content.Replace(
        '"prompt": "2. Which word has the underlined part pronounced differently from that of the others?\n\nA. plane\nB. training\nC. lack\nD. table"',
        '"prompt": "2. Which word has the underlined part pronounced differently from that of the others?\n\nA. pl<u>a</u>ne\nB. tr<u>a</u>ining\nC. l<u>a</u>ck\nD. t<u>a</u>ble"'
    )
    
    # 2024 Q1 prompt
    $content = $content.Replace(
        '"prompt": "1. Which word has the underlined part pronounced differently from that of the others?\n\nA. destroys\nB. controls\nC. predicts\nD. wanders"',
        '"prompt": "1. Which word has the underlined part pronounced differently from that of the others?\n\nA. destroy<u>s</u>\nB. control<u>s</u>\nC. predict<u>s</u>\nD. wander<u>s</u>"'
    )
    # 2024 Q2 prompt
    $content = $content.Replace(
        '"prompt": "2. Which word has the underlined part pronounced differently from that of the others?\n\nA. label\nB. campus\nC. nation\nD. parade"',
        '"prompt": "2. Which word has the underlined part pronounced differently from that of the others?\n\nA. l<u>a</u>bel\nB. c<u>a</u>mpus\nC. n<u>a</u>tion\nD. par<u>a</u>de"'
    )
    
    # 2023 Q1 prompt
    $content = $content.Replace(
        '"prompt": "1. Which word has the underlined part pronounced differently from that of the others?\n\nA. mentioned\nB. consisted\nC. described\nD. studied"',
        '"prompt": "1. Which word has the underlined part pronounced differently from that of the others?\n\nA. mention<u>ed</u>\nB. consist<u>ed</u>\nC. describ<u>ed</u>\nD. studi<u>ed</u>"'
    )
    # 2023 Q2 prompt
    $content = $content.Replace(
        '"prompt": "2. Which word has the underlined part pronounced differently from that of the others?\n\nA. village\nB. lighting\nC. litter\nD. river"',
        '"prompt": "2. Which word has the underlined part pronounced differently from that of the others?\n\nA. v<u>i</u>llage\nB. l<u>i</u>ghting\nC. l<u>i</u>tter\nD. r<u>i</u>ver"'
    )
    
    # 2022 Q1 prompt
    $content = $content.Replace(
        '"prompt": "Which word has the underlined part pronounced differently from that of the others?\n\nA. national\nB. natural\nC. carry\nD. plane"',
        '"prompt": "Which word has the underlined part pronounced differently from that of the others?\n\nA. n<u>a</u>tional\nB. n<u>a</u>tural\nC. c<u>a</u>rry\nD. pl<u>a</u>ne"'
    )
    # 2022 Q2 prompt
    $content = $content.Replace(
        '"prompt": "Which word has the underlined part pronounced differently from that of the others?\n\nA. innovated\nB. mended\nC. received\nD. celebrated"',
        '"prompt": "Which word has the underlined part pronounced differently from that of the others?\n\nA. innovat<u>ed</u>\nB. mend<u>ed</u>\nC. receiv<u>ed</u>\nD. celebrat<u>ed</u>"'
    )
    
    [System.IO.File]::WriteAllText($filePath, $content, [System.Text.Encoding]::UTF8)
}
Write-Output "Successfully updated pronunciation questions."

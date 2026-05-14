$wslIp = ""
$retry = 0
while (-not $wslIp -and $retry -lt 10) {
    Start-Sleep -Seconds 3
    $wslIp = (wsl hostname -I 2>$null).Trim().Split(" ")[0]
    $retry++
}

if (-not $wslIp) { Write-Host "WSL2 IP 실패"; exit 1 }

$envPath = "$PSScriptRoot\.env"
$content = [System.IO.File]::ReadAllText($envPath, [System.Text.Encoding]::UTF8)

# @IP:PORT/ 또는 @/ 두 패턴 모두 처리
$updated = $content -replace 'DATABASE_URL=postgresql://postgres:password@[^/]*/sleepingcare_db', "DATABASE_URL=postgresql://postgres:password@$wslIp`:5432/sleepingcare_db"

[System.IO.File]::WriteAllText($envPath, $updated, [System.Text.Encoding]::UTF8)
Write-Host "완료: $wslIp"
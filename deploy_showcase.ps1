# deploy_showcase.ps1 — 一键把 binder_showcase/ 更新到 GitHub Pages
#
# 用法(在 PowerShell 里):
#   ./binder_showcase/deploy_showcase.ps1            # 直接推送当前 binder_showcase/ 内容
#   ./binder_showcase/deploy_showcase.ps1 -Rebuild   # 先跑 build_site.py 重建 assets 再推送
#
# 站点:https://xy-xuyang123.github.io/tcr-binder-showcase/
# 说明:每次都用「单提交强制推送」，仓库永远只有 1 个 commit，不会因为 24MB 结构文件越攒越大。

param([switch]$Rebuild)
$ErrorActionPreference = "Stop"

# 确保能找到 gh(便携版装在这里)
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  $env:Path += ";C:\Users\admin\bin\gh_cli\bin"
}

$Src  = $PSScriptRoot                          # 脚本所在目录 = binder_showcase/
$Repo = "xy-xuyang123/tcr-binder-showcase"
$Url  = "https://xy-xuyang123.github.io/tcr-binder-showcase/"

# 1) 可选：重建 assets（data.js / cifs.js / pae/*.png）
if ($Rebuild) {
  Write-Host "[1/3] 重建 assets（build_site.py）..." -ForegroundColor Cyan
  python "$Src\build\build_site.py"
}

# 2) 拷到干净的临时目录，加 .nojekyll
$Stage = Join-Path $env:TEMP ("showcase_deploy_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Stage | Out-Null
Write-Host "[2/3] 打包站点内容 ..." -ForegroundColor Cyan
Copy-Item "$Src\*" $Stage -Recurse -Force
New-Item -ItemType File -Path (Join-Path $Stage ".nojekyll") -Force | Out-Null

# 3) 单提交强制推送
Write-Host "[3/3] 推送到 GitHub Pages ..." -ForegroundColor Cyan
Push-Location $Stage
try {
  git init -b main -q
  git add -A
  git -c core.autocrlf=false commit -q -m ("Update showcase " + (Get-Date -Format "yyyy-MM-dd HH:mm"))
  git remote add origin "https://github.com/$Repo.git"
  git push -f -q origin main
} finally {
  Pop-Location
  Remove-Item $Stage -Recurse -Force
}

Write-Host ""
Write-Host "[✓] 已推送。约 1 分钟后线上生效：" -ForegroundColor Green
Write-Host "    $Url" -ForegroundColor Green

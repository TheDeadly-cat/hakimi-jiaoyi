param(
    [string]$Target = "C:\Users\Administrator\Documents\Futu_OpenD_10.7.6728_Windows\Futu_OpenD_10.7.6728_Windows\Futu_OpenD_10.7.6728_Windows\FutuOpenD.xml"
)

$ErrorActionPreference = "Stop"

function ConvertTo-Md5Hex {
    param([string]$Text)
    $md5 = [System.Security.Cryptography.MD5]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        $hash = $md5.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($hash) -replace "-", "").ToLowerInvariant()
    }
    finally {
        $md5.Dispose()
    }
}

function Read-PlainPassword {
    param([System.Security.SecureString]$Secure)
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

if (-not (Test-Path -LiteralPath $Target)) {
    throw "FutuOpenD.xml not found: $Target"
}

$credential = Get-Credential -Message "请输入富途 OpenD 登录账号和密码。密码只在本机处理，不会显示在聊天里。"
if (-not $credential -or [string]::IsNullOrWhiteSpace($credential.UserName)) {
    throw "No credential was entered."
}

$plainPassword = Read-PlainPassword $credential.Password
if ([string]::IsNullOrWhiteSpace($plainPassword)) {
    throw "Password cannot be empty."
}

Get-Process -Name FutuOpenD -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

$backup = "$Target.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item -LiteralPath $Target -Destination $backup -Force

[xml]$xml = Get-Content -LiteralPath $Target -Raw -Encoding UTF8
$root = $xml.futu_opend
if (-not $root) {
    throw "Invalid FutuOpenD.xml: missing futu_opend root."
}

$root.login_account = $credential.UserName

if (-not $root.login_pwd_md5) {
    $node = $xml.CreateElement("login_pwd_md5")
    $insertAfter = $root.SelectSingleNode("login_account")
    if ($insertAfter) {
        [void]$root.InsertAfter($node, $insertAfter)
    }
    else {
        [void]$root.AppendChild($node)
    }
}

$root.login_pwd_md5 = ConvertTo-Md5Hex $plainPassword
if ($root.login_pwd) {
    $root.login_pwd = ""
}

$settings = New-Object System.Xml.XmlWriterSettings
$settings.Encoding = New-Object System.Text.UTF8Encoding($false)
$settings.Indent = $true
$settings.NewLineChars = "`r`n"
$writer = [System.Xml.XmlWriter]::Create($Target, $settings)
try {
    $xml.Save($writer)
}
finally {
    $writer.Close()
}

Write-Host ""
Write-Host "已写入 FutuOpenD 登录配置。备份文件：" -ForegroundColor Green
Write-Host $backup
Write-Host ""
Write-Host "现在可以关闭这个窗口，然后回到 Codex 告诉我：已输入。"
Read-Host "按回车关闭窗口"

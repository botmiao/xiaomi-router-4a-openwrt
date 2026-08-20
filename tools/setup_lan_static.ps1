# Set static IP (no gateway, no DNS) on the wired Ethernet adapter so that
# it only talks to the router LAN (192.168.31.x) while internet stays on WLAN.
$ErrorActionPreference = 'Continue'
$out = Join-Path $PSScriptRoot 'setup_lan_result.txt'
"=== setup_lan_static start ===" | Out-File $out -Encoding utf8

# Pick the physical wired adapter (802.3 = Ethernet; WiFi is Native802.11), link Up
$ada = Get-NetAdapter -Physical | Where-Object { $_.MediaType -eq '802.3' -and $_.Status -eq 'Up' } | Select-Object -First 1
if (-not $ada) {
    "NO_ETHERNET_ADAPTER_UP" | Out-File $out -Append -Encoding utf8
    Get-NetAdapter -Physical | Format-Table Name, ifIndex, MediaType, Status | Out-String | Out-File $out -Append -Encoding utf8
    exit 1
}
$i = $ada.ifIndex
"adapter: $($ada.Name) ifIndex=$i" | Out-File $out -Append -Encoding utf8

# Remove existing IPv4 addresses and the default route on this adapter
Get-NetIPAddress -InterfaceIndex $i -AddressFamily IPv4 -ErrorAction SilentlyContinue | Remove-NetIPAddress -Confirm:$false -ErrorAction SilentlyContinue
Remove-NetRoute -InterfaceIndex $i -DestinationPrefix '0.0.0.0/0' -Confirm:$false -ErrorAction SilentlyContinue

# Static IP without default gateway
try {
    New-NetIPAddress -InterfaceIndex $i -IPAddress 192.168.31.228 -PrefixLength 24 -ErrorAction Stop | Out-Null
    "static ip set OK" | Out-File $out -Append -Encoding utf8
} catch {
    "static ip FAILED: $($_.Exception.Message)" | Out-File $out -Append -Encoding utf8
}

# Reset DNS on this adapter (no DNS servers on wired link)
Set-DnsClientServerAddress -InterfaceIndex $i -ResetServerAddresses -ErrorAction SilentlyContinue
"=== final state ===" | Out-File $out -Append -Encoding utf8
Get-NetIPAddress -InterfaceIndex $i -AddressFamily IPv4 -ErrorAction SilentlyContinue | Format-Table IPAddress, PrefixLength | Out-String | Out-File $out -Append -Encoding utf8
Get-NetRoute -InterfaceIndex $i -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Format-Table -AutoSize | Out-String | Out-File $out -Append -Encoding utf8
"=== done ===" | Out-File $out -Append -Encoding utf8

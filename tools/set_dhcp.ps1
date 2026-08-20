# Switch the wired Ethernet adapter back to DHCP so the PC can get an address
# from the OpenWrt initramfs system (192.168.1.x).
$out = Join-Path $PSScriptRoot 'dhcp_result.txt'
"=== set dhcp start ===" | Out-File $out -Encoding utf8
$ada = Get-NetAdapter -Physical | Where-Object { $_.MediaType -eq '802.3' -and $_.Status -eq 'Up' } | Select-Object -First 1
if (-not $ada) { "NO_ETHERNET" | Out-File $out -Append -Encoding utf8; exit 1 }
$i = $ada.ifIndex
"adapter: $($ada.Name) ifIndex=$i" | Out-File $out -Append -Encoding utf8
Get-NetIPAddress -InterfaceIndex $i -AddressFamily IPv4 -ErrorAction SilentlyContinue | Remove-NetIPAddress -Confirm:$false -ErrorAction SilentlyContinue
Remove-NetRoute -InterfaceIndex $i -DestinationPrefix '0.0.0.0/0' -Confirm:$false -ErrorAction SilentlyContinue
Set-NetIPInterface -InterfaceIndex $i -Dhcp Enabled -ErrorAction SilentlyContinue
Set-DnsClientServerAddress -InterfaceIndex $i -ResetServerAddresses -ErrorAction SilentlyContinue
# trigger renew
$null = & ipconfig /renew "$($ada.Name)" 2>&1
Start-Sleep -Seconds 8
Get-NetIPAddress -InterfaceIndex $i -AddressFamily IPv4 -ErrorAction SilentlyContinue | Format-Table IPAddress, PrefixLength | Out-String | Out-File $out -Append -Encoding utf8
"=== done ===" | Out-File $out -Append -Encoding utf8

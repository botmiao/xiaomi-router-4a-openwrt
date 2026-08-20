import os, sys, requests, re, time, random, hashlib, tarfile, io, socket, threading, datetime
ip='192.168.31.1'; pwd=os.environ.get('ROUTER_PWD') or sys.exit('请先设置环境变量 ROUTER_PWD（小米后台管理密码）'); myip='192.168.31.228'  # myip=本机有线网卡IP，按需修改
FW=os.path.abspath('../firmware/openwrt-25.12.5-ramips-mt7621-xiaomi_mi-router-4a-gigabit-initramfs-kernel.bin')
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0'}
served=[False]
def listener():
    srv=socket.socket(); srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    srv.bind(('0.0.0.0',9999)); srv.listen(16); srv.settimeout(300)
    try:
        while True:
            c,a=srv.accept()
            try: req=c.recv(300).decode(errors='replace')
            except Exception: req=''
            path=req.split(' ')[1] if ' ' in req else '/'
            if path.startswith('/initramfs'):
                data=open(FW,'rb').read()
                c.sendall(b'HTTP/1.0 200 OK\r\nContent-Length: %d\r\n\r\n'%len(data)+data)
                served[0]=True
                print('  *** initramfs served: %d bytes ***'%len(data),flush=True)
            else:
                c.sendall(b'HTTP/1.0 200 OK\r\nContent-Length: 2\r\n\r\nok')
            c.close()
    except socket.timeout: pass
threading.Thread(target=listener,daemon=True).start()

r0=requests.get('http://%s/cgi-bin/luci/web'%ip,timeout=8,headers=UA)
mac=re.findall(r"deviceId = '(.*?)'",r0.text)[0]
key=re.findall(r"key: '(.*)',",r0.text)[0]
nonce='0_%s_%d_%d'%(mac,int(time.time()),random.randint(10000,99999))
h1=hashlib.sha1((pwd+key).encode()).hexdigest()
h2=hashlib.sha1((nonce+h1).encode()).hexdigest()
r=requests.post('http://%s/cgi-bin/luci/api/xqsystem/login'%ip,data='username=admin&password=%s&logtype=2&nonce=%s'%(h2,nonce),headers=dict(UA,**{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'}),timeout=8)
stok=r.json()['token']

cmd=("/bin/busybox wget -T 10 -q -O /tmp/fw.bin http://{m}:9999/initramfs.bin; /bin/sh -c 'trap "" INT TERM HUP; exec /sbin/mtd -r write /tmp/fw.bin OS1'".format(m=myip))
items1='\n'.join('\t\t<item url="http://%s:9998/f%d.dat"/>'%(myip,i) for i in range(14))
xml='<?xml version="1.0"?>\n<root>\n\t<class type="1">\n%s\n\t</class>\n\t<class type="2">\n\t\t<item url="http://%s -q -O /dev/null;%s;exit;wget http://%s "/>\n\t</class>\n\t<class type="3">\n\t\t<item uploadurl="http://%s:9998/up"/>\n\t</class>\n</root>\n'%(items1,ip,cmd,ip,myip)

buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz',format=tarfile.GNU_FORMAT) as t:
    for name,data in [('cfg_backup.des',open('backup_unpack/cfg_backup.des','rb').read()),
                      ('cfg_backup.mbu',open('backup_unpack/cfg_backup.mbu','rb').read()),
                      ('speedtest_urls.xml',xml.encode())]:
        ti=tarfile.TarInfo(name); ti.size=len(data); ti.mode=0o644
        t.addfile(ti,io.BytesIO(data))
payload=buf.getvalue()
now=datetime.datetime.now()
fname='%04d-%02d-%02d--%02d %02d %02d.tar.gz'%(now.year,now.month,now.day,now.hour,now.minute,now.second)
rr=requests.post('http://%s/cgi-bin/luci/;stok=%s/api/misystem/c_upload'%(ip,stok),files={'image':(fname,payload)},headers=UA,timeout=30)
print('c_upload:',rr.text[:40],flush=True)
time.sleep(2)
rr=requests.get('http://%s/cgi-bin/luci/;stok=%s/api/xqnetdetect/netspeed?0'%(ip,stok),headers=UA,timeout=30)
print('netspeed:',rr.text[:40],flush=True)
for i in range(30):
    time.sleep(3)
    if served[0]:
        print('t+%ds: firmware downloaded, mtd writing/rebooting...'%((i+1)*3),flush=True)
        break
else:
    print('WARNING: firmware never downloaded',flush=True)
print('done. router will reboot into OpenWrt initramfs (192.168.1.1)',flush=True)

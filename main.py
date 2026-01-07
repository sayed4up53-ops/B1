import sys, os, requests, string, random, time, functools

# ضمان الطباعة الفورية
os.environ['PYTHONUNBUFFERED'] = "1"
print = functools.partial(print, flush=True)

# --- الإعدادات ---
BROWSERLESS_TOKEN = "2TkB7Bi7dGeDk2p601084c4fa52bbda0003cd2f2114350d9b"
SHEET_API_URL = "https://api.sheetbest.com/sheets/b40a7f06-4a7a-4fe4-a01c-d81372d85a87" 
MAIL_TM_API = "https://api.mail.tm"
ACCOUNTS_PER_RUN = 5 

def generate_random_username(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def create_temp_email():
    try:
        print("📧 جاري طلب نطاق بريد...")
        domains_res = requests.get(f"{MAIL_TM_API}/domains", timeout=30).json()
        domain = domains_res['hydra:member'][0]['domain']
        email = f"{generate_random_username()}@{domain}"
        password = generate_random_username(12)
        requests.post(f"{MAIL_TM_API}/accounts", json={"address": email, "password": password}, timeout=30)
        token_res = requests.post(f"{MAIL_TM_API}/token", json={"address": email, "password": password}, timeout=30).json()
        return email, password, token_res['token']
    except Exception as e:
        print(f"❌ فشل إنشاء البريد: {e}")
        return None, None, None

print("🚀 انطلاق البوت في الدورة الحالية...")

for i in range(ACCOUNTS_PER_RUN):
    print(f"\n{'─'*30}\n🔄 الحساب رقم {i+1} من {ACCOUNTS_PER_RUN}")
    
    email, password, auth_token = create_temp_email()
    if not email: continue
    print(f"✅ تم تجهيز: {email}")

    script = f"""
    export default async ({{ page }}) => {{
      const wait = (ms) => new Promise(res => setTimeout(res, ms));
      try {{
        await page.goto('https://account.browserless.io/signup/email/?plan=free', {{ waitUntil: 'networkidle2', timeout: 60000 }});
        await page.type('input[placeholder="Your Email"]', '{email}');
        await page.evaluate(() => {{
          const b = Array.from(document.querySelectorAll('button')).find(x => x.innerText.includes('Verify'));
          if (b) b.click();
        }});
        
        let code = null;
        for (let j = 0; j < 15; j++) {{
          const res = await fetch('https://api.mail.tm/messages', {{ headers: {{ 'Authorization': 'Bearer {auth_token}' }} }});
          const data = await res.json();
          if (data['hydra:member']?.[0]) {{
            const msg = await fetch(`https://api.mail.tm/messages/${{data['hydra:member'][0].id}}`, {{ headers: {{ 'Authorization': 'Bearer {auth_token}' }} }}).then(r => r.json());
            const m = (msg.text || '').match(/\\b(\\d{{6}})\\b/);
            if (m) {{ code = m[1]; break; }}
          }}
          await wait(6000);
        }}
        if (!code) throw new Error('Timeout Code');
        
        await page.type('input[placeholder="000 000"]', code);
        await wait(3000);
        await page.evaluate(() => {{
          const b = Array.from(document.querySelectorAll('button')).find(x => x.innerText.includes('Submit'));
          if (b) b.click();
        }});
        
        await page.waitForSelector('input[placeholder="John Doe"]', {{ visible: true, timeout: 30000 }});
        await page.type('input[placeholder="John Doe"]', 'User_' + Math.random().toString(36).slice(2,7));
        await page.click('#attribution-select button');
        await wait(1000); await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter');
        await page.click('input[type="checkbox"]');
        await wait(2000);
        await page.click('[data-testid="complete-signup-button"]');
        
        await wait(15000);
        const apiKey = await page.evaluate(async () => {{
            return new Promise((res) => {{
                navigator.clipboard.writeText = (t) => res(t);
                const b = document.querySelector('button[title="Copy API Key"]');
                if(b) b.click(); else setTimeout(() => res("Not_Found"), 5000);
            }});
        }});
        return {{ success: true, key: apiKey }};
      }} catch (e) {{ return {{ success: false, err: e.message }}; }}
    }};
    """

    try:
        print("🌐 جاري استخراج المفتاح عبر Browserless...")
        # قمت بتغيير السيرفر إلى واحد أكثر استقراراً
        response = requests.post(
            f"https://production-sfo.browserless.io/function?token={BROWSERLESS_TOKEN}",
            json={"code": script.strip()},
            timeout=180
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                key = result.get('key')
                print(f"✨ تم النجاح! المفتاح: {key}")
                requests.post(SHEET_API_URL, json={
                    "Email": email, "Password": password, "API_Key": key, "Date": time.strftime("%H:%M:%S")
                })
                print("💾 تم الحفظ في الجدول.")
            else:
                print(f"❌ فشل المتصفح: {result.get('err')}")
        else:
            print(f"⚠️ سيرفر Browserless رد برمز: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ خطأ عام: {e}")
    
    time.sleep(5)

print("\n🏁 اكتملت الدورة.")

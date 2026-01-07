import requests
import string
import random
import time
import sys

# --- الإعدادات ---
BROWSERLESS_TOKEN = "2TkB7Bi7dGeDk2p601084c4fa52bbda0003cd2f2114350d9b"
SHEET_API_URL = "https://api.sheetbest.com/sheets/b40a7f06-4a7a-4fe4-a01c-d81372d85a87"
MAIL_TM_API = "https://api.mail.tm"

def generate_random_username(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def create_temp_email():
    try:
        domains_res = requests.get(f"{MAIL_TM_API}/domains", timeout=10).json()
        domain = domains_res['hydra:member'][0]['domain']
        email = f"{generate_random_username()}@{domain}"
        password = generate_random_username(12)
        
        # إنشاء الحساب
        reg_res = requests.post(f"{MAIL_TM_API}/accounts", json={"address": email, "password": password}, timeout=10)
        if reg_res.status_code != 201:
            return None, None, None
            
        # الحصول على التوكن
        token_res = requests.post(f"{MAIL_TM_API}/token", json={"address": email, "password": password}, timeout=10).json()
        return email, password, token_res['token']
    except Exception as e:
        print(f"⚠️ خطأ في إنشاء الإيميل: {e}")
        return None, None, None

# حدد عدد الحسابات التي تريد إنشاءها في المرة الواحدة (مثلاً 5) لتجنب الحظر أو التوقف المفاجئ
MAX_ACCOUNTS = 5 

for i in range(MAX_ACCOUNTS):
    print(f"\n🔄 محاولة إنشاء الحساب رقم {i+1}...")
    email, password, auth_token = create_temp_email()
    
    if not email:
        print("⏭️ فشل إنشاء إيميل مؤقت، تخطي...")
        continue

    # الكود البرمجي الذي يرسل لـ Browserless
    script = f"""
    export default async ({{ page }}) => {{
      const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));
      
      async function getCode() {{
        try {{
          const res = await fetch('https://api.mail.tm/messages', {{ 
            headers: {{ 'Authorization': 'Bearer {auth_token}' }} 
          }});
          const data = await res.json();
          const msg = data['hydra:member']?.[0];
          if (msg) {{
            const detail = await fetch(`https://api.mail.tm/messages/${{msg.id}}`, {{ 
                headers: {{ 'Authorization': 'Bearer {auth_token}' }} 
            }}).then(r => r.json());
            const match = (detail.text || '').match(/\\b(\\d{{6}})\\b/);
            return match ? match[1] : null;
          }}
        } catch(e) {{}}
        return null;
      }}

      try {{
        await page.goto('https://account.browserless.io/signup/email/?plan=free', {{ waitUntil: 'networkidle2' }});
        await page.waitForSelector('input[placeholder="Your Email"]');
        await page.type('input[placeholder="Your Email"]', '{email}');
        
        await page.evaluate(() => {{
          const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Verify'));
          if (btn) btn.click();
        }});

        let code = null;
        for (let j = 0; j < 15; j++) {{
          code = await getCode();
          if (code) break;
          await wait(5000);
        }}
        if (!code) throw new Error('Email Code Timeout');

        await page.waitForSelector('input[placeholder="000 000"]');
        await page.type('input[placeholder="000 000"]', code);
        await wait(2000);
        
        await page.evaluate(() => {{
            const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Submit code'));
            if (btn) btn.click();
        }});

        await page.waitForSelector('input[placeholder="John Doe"]', {{ visible: true, timeout: 15000 }});
        await page.type('input[placeholder="John Doe"]', 'Dev_' + Math.random().toString(36).substring(7));
        
        await page.click('#attribution-select button');
        await wait(1000);
        await page.keyboard.press('ArrowDown');
        await page.keyboard.press('Enter');
        
        await page.click('input[type="checkbox"]');
        await wait(1000);
        await page.click('[data-testid="complete-signup-button"]');

        await wait(10000); 

        let copyBtn = await page.$('button[title="Copy API Key"]');
        if (!copyBtn) {{
            await page.reload({{ waitUntil: 'networkidle2' }});
            await wait(5000);
        }}

        await page.waitForSelector('button[title="Copy API Key"]', {{ timeout: 20000 }});
        
        const fullKey = await page.evaluate(async () => {{
            return new Promise((resolve) => {{
                navigator.clipboard.writeText = async (text) => resolve(text);
                const btn = document.querySelector('button[title="Copy API Key"]');
                if (btn) btn.click();
                setTimeout(() => resolve("Failed_to_Capture"), 6000);
            }});
        }});

        return {{ success: true, apiKey: fullKey }};
      }} catch (e) {{ 
        return {{ success: false, error: e.message }}; 
      }}
    }};
    """

    try:
        response = requests.post(
            f"https://production-sfo.browserless.io/function?token={BROWSERLESS_TOKEN}",
            headers={"Content-Type": "application/json"},
            json={"code": script.strip()},
            timeout=300
        )
        result = response.json()
        
        if result.get('success') and result.get('apiKey') != "Failed_to_Capture":
            api_key = result.get('apiKey')
            print(f"✅ نجاح: {api_key}")
            row_data = {"Email": email, "Password": password, "API_Key": api_key, "Date": time.strftime("%Y-%m-%d %H:%M:%S")}
            requests.post(SHEET_API_URL, json=row_data)
            print("💾 تم الحفظ في SheetBest.")
        else:
            print(f"❌ خطأ من المتصفح: {result.get('error', 'فشل التقاط المفتاح')}")
            
    except Exception as e:
        print(f"⚠️ خطأ اتصال: {e}")

    print("💤 استراحة 10 ثوانٍ قبل الحساب التالي...")
    time.sleep(10)

print("\n✅ انتهت العملية.")

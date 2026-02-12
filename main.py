import requests
from flask import Flask, request, render_template_string
import qrcode
import io
import base64
from datetime import datetime
import pytz

app = Flask(__name__)

URL_ASSINADOR = "http://35.241.41.66"

HTML_PAINEL = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>POS MANUAL INJECTOR v3.6</title>
    <style>
        body { background-color: #000; color: #0f0; font-family: monospace; padding: 20px; }
        .container { max-width: 600px; margin: auto; border: 2px solid #0f0; padding: 20px; background: #050505; }
        .row { display: flex; gap: 10px; margin-top: 10px; }
        label { display: block; font-size: 0.8rem; margin-top: 10px; color: #888; }
        input { background: #000; color: #fff; border: 1px solid #0f0; padding: 10px; width: 100%; box-sizing: border-box; }
        button { background: #0f0; color: #000; border: none; padding: 15px; width: 100%; margin-top: 20px; font-weight: bold; cursor: pointer; width: 100%; }
        .result { margin-top: 20px; padding: 15px; border: 1px dashed #0f0; text-align: center; }
        .payload-box { word-break: break-all; font-size: 0.75rem; background: #111; padding: 10px; color: #0f0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>POS MANUAL SIGNER v3.6</h1>
        <form action="/gerar" method="post">
            <div class="row">
                <div style="flex:1">
                    <label>ID MÁQUINA (i:)</label>
                    <input type="text" name="terminal" value="14" required>
                </div>
                <div style="flex:1">
                    <label>PREFIXO (u:) +15</label>
                    <input type="text" name="prefixo" placeholder="Ex: 854728897" required>
                </div>
            </div>
            <div class="row">
                <div style="flex:1">
                    <label>TARIFA (Fixa)</label>
                    <input type="text" name="tarifa" value="540" readonly style="color: #555;">
                </div>
                <div style="flex:1">
                    <label>DATA/HORA (YYYYMMDDHHMMSS)</label>
                    <input type="text" name="data_hora" id="data_hora">
                </div>
            </div>
            <label>DNA DA MATRIZ (PRIMEIROS 32 BYTES DO CAMPO C:)</label>
            <input type="text" name="key_publica" placeholder="Cole aqui os 32 caracteres iniciais..." required>
            <button type="submit">GERAR ASSINATURA PRIVADA</button>
        </form>
        <script>
            const now = new Date();
            const pad = (n) => n.toString().padStart(2, '0');
            document.getElementById('data_hora').value = now.getFullYear() + pad(now.getMonth()+1) + pad(now.getDate()) + pad(now.getHours()) + pad(now.getMinutes()) + pad(now.getSeconds());
        </script>
        {% if payload %}<div class="result"><label>QR GERADO:</label><div class="payload-box">{{ payload }}</div><img src="data:image/png;base64,{{ qr_code }}" style="border:10px solid #fff; margin-top:10px;"></div>{% endif %}
        {% if erro %}<div class="result" style="color:red;">{{ erro }}</div>{% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAINEL)

@app.route('/gerar', methods=['POST'])
def gerar():
    terminal = request.form.get('terminal')
    prefixo = request.form.get('prefixo')
    tarifa = "540"
    data_hora = request.form.get('data_hora')
    key_pub = request.form.get('key_publica').strip()

    # SEQUÊNCIA BRUTA: Terminal + Prefixo + Tarifa + Data + DNA
    payload_envio = f"{terminal}{prefixo}{tarifa}{data_hora}{key_pub}"
    
    headers = {'User-Agent': 'okhttp/3.14.9', 'Content-Type': 'text/plain', 'Connection': 'close'}

    try:
        r = requests.post(URL_ASSINADOR, data=payload_envio, headers=headers, timeout=12)
        if r.status_code == 200 and r.text:
            assinatura_privada = r.text.strip()
            # O Payload final concatena a Key Pública (DNA) com a Assinatura Privada que o servidor devolveu
            final = f"<q:01>s:196;u:{prefixo};i:{terminal};c:{key_pub}{assinatura_privada};x:64;"
            img = qrcode.make(final)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            qr_b64 = base64.b64encode(buf.getvalue()).decode()
            return render_template_string(HTML_PAINEL, payload=final, qr_code=qr_b64)
        else:
            return render_template_string(HTML_PAINEL, erro=f"Servidor recusou (HTTP {r.status_code})")
    except:
        return render_template_string(HTML_PAINEL, erro="Conexão fechada. Verifique a ordem dos dados.")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

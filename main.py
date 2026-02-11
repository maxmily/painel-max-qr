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
    <title>POS MANUAL INJECTOR v3.5</title>
    <style>
        body { background-color: #000; color: #0f0; font-family: monospace; padding: 20px; }
        .container { max-width: 600px; margin: auto; border: 1px solid #0f0; padding: 20px; background: #050505; }
        .row { display: flex; gap: 10px; margin-top: 10px; }
        .col { flex: 1; }
        label { display: block; font-size: 0.8rem; margin-bottom: 5px; color: #888; }
        input { background: #000; color: #fff; border: 1px solid #0f0; padding: 10px; width: 100%; box-sizing: border-box; }
        button { background: #0f0; color: #000; border: none; padding: 15px; width: 100%; margin-top: 20px; font-weight: bold; cursor: pointer; }
        .result { margin-top: 20px; padding: 15px; border: 1px dashed #0f0; text-align: center; }
        .payload-box { word-break: break-all; font-size: 0.75rem; background: #111; padding: 10px; color: #0f0; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>DEBUG: MANUAL SIGNER</h1>
        <p style="font-size: 0.7rem; color: #f00;">TESTE DE SEQUÊNCIA BRUTA PARA O SERVIDOR</p>
        
        <form action="/gerar" method="post">
            <div class="row">
                <div class="col">
                    <label>ID MÁQUINA (i:)</label>
                    <input type="text" name="terminal" placeholder="Ex: 14" required>
                </div>
                <div class="col">
                    <label>PREFIXO ATUAL (u:)</label>
                    <input type="text" name="prefixo" placeholder="Ex: 854728897" required>
                </div>
            </div>

            <div class="row">
                <div class="col">
                    <label>TARIFA (Ex: 0440)</label>
                    <input type="text" name="tarifa" value="0440" required>
                </div>
                <div class="col">
                    <label>DATA/HORA (YYYYMMDDHHMMSS)</label>
                    <input type="text" name="data_hora" id="data_hora">
                </div>
            </div>

            <label style="margin-top:15px;">KEY PÚBLICA (DNA 32 BYTES):</label>
            <input type="text" name="key_publica" placeholder="Cole os 32 caracteres do campo c:" required>

            <button type="submit">TESTAR SEQUÊNCIA E ASSINAR</button>
        </form>

        <script>
            // Preenche a data automática mas permite editar
            function updateTime() {
                const now = new Date();
                const pad = (n) => n.toString().padStart(2, '0');
                const ts = now.getFullYear() + pad(now.getMonth()+1) + pad(now.getDate()) + 
                           pad(now.getHours()) + pad(now.getMinutes()) + pad(now.getSeconds());
                document.getElementById('data_hora').value = ts;
            }
            updateTime();
        </script>

        {% if payload %}
        <div class="result">
            <label>RESPOSTA DO SERVIDOR:</label>
            <div class="payload-box">{{ payload }}</div>
            <img src="data:image/png;base64,{{ qr_code }}" style="border:10px solid #fff;">
        </div>
        {% endif %}
        
        {% if erro %}
        <div class="result" style="color: #f00; border-color: #f00;">
            <label>STATUS DE ERRO:</label>
            <p>{{ erro }}</p>
        </div>
        {% endif %}
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
    tarifa = request.form.get('tarifa')
    data_hora = request.form.get('data_hora')
    key_pub = request.form.get('key_publica').strip()

    # MONTAGEM DA SEQUÊNCIA (O coração do teste)
    # Você pode mudar a ordem aqui se o servidor continuar fechando
    payload_envio = f"{terminal}{prefixo}{tarifa}{data_hora}{key_pub}"
    
    headers = {
        'User-Agent': 'okhttp/3.14.9',
        'Content-Type': 'text/plain',
        'Connection': 'close'
    }

    try:
        # Tenta enviar a sequência manual
        r = requests.post(URL_ASSINADOR, data=payload_envio, headers=headers, timeout=12)
        
        if r.status_code == 200 and r.text:
            assinatura = r.text.strip()
            # Monta o QR com o prefixo que você digitou
            final = f"<q:01>s:196;u:{prefixo};i:{terminal};c:{assinatura};x:64;"
            
            img = qrcode.make(final)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            qr_b64 = base64.b64encode(buf.getvalue()).decode()
            
            return render_template_string(HTML_PAINEL, payload=final, qr_code=qr_b64)
        else:
            return render_template_string(HTML_PAINEL, erro=f"Servidor recusou (HTTP {r.status_code}). Resposta: {r.text}")
            
    except Exception as e:
        return render_template_string(HTML_PAINEL, erro=f"Conexão Fechada. Sequência tentada: {payload_envio}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

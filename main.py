import requests
from flask import Flask, request, render_template_string
import qrcode
import io
import base64
from datetime import datetime
import pytz # Certifique-se de que 'pytz' esteja no seu requirements.txt

app = Flask(__name__)

URL_ASSINADOR = "http://35.241.41.66"

@app.route('/')
def index():
    return render_template_string(HTML_PAINEL)

@app.route('/gerar', methods=['POST'])
def gerar():
    matriz = request.form.get('matriz')
    try:
        # 1. Extração dos dados
        u_original = matriz.split('u:')[1].split(';')[0]
        terminal_real = matriz.split('i:')[1].split(';')[0] 
        dna_key_publica = matriz.split('c:')[1].split(';')[0][:32]
        
        # 2. Dados da Sequência com Horário de Brasília
        u_novo = str(int(u_original) + 15)
        tarifa = "440"
        
        # Forçando o horário de Brasília (importante para bater com o servidor)
        fuso = pytz.timezone('America/Sao_Paulo')
        data_hora = datetime.now(fuso).strftime("%Y%m%d%H%M%S")
        
        # 3. Montagem da Sequência Bruta
        payload_envio = f"{terminal_real}{u_novo}{tarifa}{data_hora}{dna_key_publica}"
        
        # HEADERS AGRESSIVOS PARA EVITAR ERRO 104
        # Simulando uma conexão de hardware real
        headers = {
            'User-Agent': 'okhttp/3.14.9',
            'Content-Type': 'application/octet-stream', # Dados binários/brutos
            'Accept-Encoding': 'gzip',
            'Connection': 'close',
            'Content-Length': str(len(payload_envio))
        }

        try:
            # Enviando a sequência exata para gerar a Key Privada
            resposta = requests.post(URL_ASSINADOR, data=payload_envio, headers=headers, timeout=15)
            
            if resposta.status_code == 200:
                assinatura_privada = resposta.text.strip()
                payload_final = f"<q:01>s:196;u:{u_novo};i:{terminal_real};c:{assinatura_privada};x:64;"
                
                img = qrcode.make(payload_final)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                qr_b64 = base64.b64encode(buf.getvalue()).decode()
                
                return render_template_string(HTML_PAINEL, payload=payload_final, qr_code=qr_b64)
            else:
                return render_template_string(HTML_PAINEL, erro=f"Servidor recusou: Código {resposta.status_code}")
                
        except Exception as e:
            # Se der erro 104 aqui, o servidor está bloqueando o IP do Render
            return render_template_string(HTML_PAINEL, erro="Erro 104: Conexão resetada. O servidor bloqueou o pedido.")

    except Exception as e:
        return render_template_string(HTML_PAINEL, erro=f"Erro: {str(e)}")

# HTML DO PAINEL (O MESMO QUE VOCÊ JÁ TEM)
HTML_PAINEL = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>AUTOPASS POS ENGINE v3.5</title>
    <style>
        body { background-color: #000; color: #0f0; font-family: monospace; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { width: 95%; max-width: 500px; border: 2px solid #0f0; padding: 20px; background: #050505; box-shadow: 0 0 10px #0f0; }
        input { background: #000; color: #0f0; border: 1px solid #0f0; padding: 12px; width: 100%; box-sizing: border-box; margin-top: 10px; }
        button { background: #0f0; color: #000; border: none; padding: 15px; width: 100%; margin-top: 20px; font-weight: bold; cursor: pointer; }
        .result { margin-top: 20px; text-align: center; border-top: 1px dotted #0f0; padding-top: 15px; }
        .payload-box { word-break: break-all; font-size: 0.8rem; background: #111; padding: 10px; border: 1px solid #333; }
        img { border: 10px solid #fff; margin-top: 15px; max-width: 100%; }
    </style>
</head>
<body>
    <div class="container">
        <h1>POS PRIVATE SIGNER</h1>
        <form action="/gerar" method="post">
            <input type="text" name="matriz" placeholder="Cole a Matriz Mãe aqui..." required>
            <button type="submit">VALIDAR E ASSINAR</button>
        </form>
        {% if payload %}<div class="result"><div class="payload-box">{{ payload }}</div><img src="data:image/png;base64,{{ qr_code }}"></div>{% endif %}
        {% if erro %}<div class="result" style="color:red;">{{ erro }}</div>{% endif %}
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

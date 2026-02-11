import requests
from flask import Flask, request, render_template_string
import qrcode
import io
import base64

app = Flask(__name__)

# URL do Servidor Assinador (raiz, sem pastas)
URL_ASSINADOR = "http://35.241.41.66"

HTML_PAINEL = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>AUTOPASS POS ENGINE v3.5 - RAW INJECTOR</title>
    <style>
        body { background-color: #000; color: #0f0; font-family: monospace; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { width: 90%; max-width: 500px; border: 2px solid #0f0; padding: 20px; box-shadow: 0 0 15px #0f0; background: #050505; }
        h1 { text-align: center; font-size: 1.2rem; border-bottom: 1px solid #0f0; padding-bottom: 10px; }
        input { background: #000; color: #0f0; border: 1px solid #0f0; padding: 12px; width: 100%; box-sizing: border-box; margin-top: 10px; }
        button { background: #0f0; color: #000; border: none; padding: 15px; width: 100%; margin-top: 20px; font-weight: bold; cursor: pointer; }
        .result { margin-top: 20px; text-align: center; border-top: 1px dotted #0f0; padding-top: 15px; }
        .payload-box { word-break: break-all; font-size: 0.8rem; background: #111; padding: 10px; border: 1px solid #333; margin-top: 10px; color: #0f0; }
        img { border: 10px solid #fff; margin-top: 15px; max-width: 100%; }
    </style>
</head>
<body>
    <div class="container">
        <h1>POS RAW DATA INJECTOR</h1>
        <form action="/gerar" method="post">
            <label>MATRIZ MÃE:</label>
            <input type="text" name="matriz" placeholder="Cole o payload original aqui..." required>
            <button type="submit">ENVIAR DADOS BRUTOS AO SERVIDOR</button>
        </form>

        {% if payload %}
        <div class="result">
            <label>RESPOSTA DO SERVIDOR (PAYLOAD FINAL):</label>
            <div class="payload-box">{{ payload }}</div>
            <img src="data:image/png;base64,{{ qr_code }}">
            <p><a href="/" style="color: #0f0;">[ NOVO TESTE ]</a></p>
        </div>
        {% endif %}
        
        {% if erro %}
        <div class="result" style="color: #f00;">
            <label>ERRO DE COMUNICAÇÃO:</label>
            <p>{{ erro }}</p>
            <a href="/" style="color: #f00;">VOLTAR</a>
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
    matriz = request.form.get('matriz')
    try:
        # Extração dos dados para envio bruto
        u_original = matriz.split('u:')[1].split(';')[0]
        terminal = matriz.split('i:')[1].split(';')[0]
        dna_mae = matriz.split('c:')[1].split(';')[0][:32] # Os 32 bytes como chave
        u_novo = str(int(u_original) + 15)

        # MONTAGEM DOS DADOS BRUTOS (Como você sugeriu)
        # Enviamos os campos isolados para o servidor processar
        dados_brutos = {
            'terminal': terminal,
            'prefixo': u_novo,
            'key': dna_mae
        }
        
        headers = {
            'User-Agent': 'okhttp/3.12.1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Connection': 'close'
        }

        try:
            # Envia os dados e espera o payload completo de volta
            resposta = requests.post(URL_ASSINADOR, data=dados_brutos, headers=headers, timeout=12)
            
            if resposta.status_code == 200 and resposta.text:
                payload_recebido = resposta.text.strip()
                
                # Gera o QR com EXATAMENTE o que o servidor devolveu
                img = qrcode.make(payload_recebido)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                qr_b64 = base64.b64encode(buf.getvalue()).decode()
                
                return render_template_string(HTML_PAINEL, payload=payload_recebido, qr_code=qr_b64)
            else:
                return render_template_string(HTML_PAINEL, erro=f"Servidor recusou os dados (Status {resposta.status_code})")
                
        except Exception as e:
            return render_template_string(HTML_PAINEL, erro=f"Conexão abortada pelo servidor. Verifique se o IP aceita dados brutos via POST.")

    except Exception as e:
        return render_template_string(HTML_PAINEL, erro=f"Erro na extração da matriz: {str(e)}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

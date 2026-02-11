import requests
from flask import Flask, request, render_template_string
import qrcode
import io
import base64

app = Flask(__name__)

# Configuração do Servidor de Injeção (Apenas o IP, sem caminhos extras)
URL_ASSINADOR = "http://35.241.41.66"

HTML_PAINEL = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AUTOPASS POS ENGINE v3.5</title>
    <style>
        body { background-color: #000; color: #0f0; font-family: 'Courier New', monospace; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { width: 90%; max-width: 500px; border: 2px solid #0f0; padding: 20px; box-shadow: 0 0 15px #0f0; background: #050505; }
        h1 { text-align: center; font-size: 1.5rem; text-transform: uppercase; border-bottom: 1px solid #0f0; padding-bottom: 10px; }
        label { display: block; margin-top: 15px; font-weight: bold; }
        input { background: #000; color: #0f0; border: 1px solid #0f0; padding: 12px; width: 100%; box-sizing: border-box; margin-top: 5px; font-family: monospace; }
        button { background: #0f0; color: #000; border: none; padding: 15px; width: 100%; margin-top: 20px; font-weight: bold; cursor: pointer; text-transform: uppercase; }
        button:hover { background: #0a0; }
        .result { margin-top: 20px; text-align: center; border-top: 1px dotted #0f0; padding-top: 15px; }
        .payload-box { word-break: break-all; font-size: 0.8rem; background: #111; padding: 10px; border: 1px solid #333; margin-top: 10px; }
        img { border: 10px solid #fff; margin-top: 15px; max-width: 100%; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AUTOPASS POS INJECTOR</h1>
        <p style="font-size: 0.7rem; text-align: center;">STATUS: [ SYSTEM ONLINE ]</p>
        
        <form action="/gerar" method="post">
            <label>MATRIZ MÃE (QR ORIGINAL):</label>
            <input type="text" name="matriz" placeholder="Cole o s:;u:;i:;c:;x: aqui..." required>
            
            <button type="submit">EXECUTAR INJEÇÃO E GERAR QR</button>
        </form>

        {% if payload %}
        <div class="result">
            <label>PAYLOAD GERADO:</label>
            <div class="payload-box">{{ payload }}</div>
            <img src="data:image/png;base64,{{ qr_code }}">
            <p><a href="/" style="color: #0f0; text-decoration: none;">[ LIMPAR E VOLTAR ]</a></p>
        </div>
        {% endif %}
        
        {% if erro %}
        <div class="result" style="color: #f00; border-color: #f00;">
            <label>ERRO NO SISTEMA:</label>
            <p>{{ erro }}</p>
            <a href="/" style="color: #f00;">TENTAR NOVAMENTE</a>
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
        # 1. Extração cirúrgica dos dados
        u_original = matriz.split('u:')[1].split(';')[0]
        terminal = matriz.split('i:')[1].split(';')[0]
        dna_mae = matriz.split('c:')[1].split(';')[0][:32] # 32 bytes de segurança
        
        # 2. Lógica de Salto (+15)
        u_novo = str(int(u_original) + 15)
        
        # 3. Pacote para o Servidor
        payload_pedido = f"{terminal}{u_novo}{dna_mae}"
        
        # Cabeçalhos para evitar o 'Remote Disconnected'
        headers = {
            'User-Agent': 'okhttp/3.12.1',
            'Content-Type': 'text/plain; charset=utf-8',
            'Connection': 'close'
        }

        try:
            # Requisição direta para o IP
            resposta = requests.post(URL_ASSINADOR, data=payload_pedido, headers=headers, timeout=10)
            
            if resposta.status_code == 200:
                assinatura_final = resposta.text.strip()
                # Se a resposta vier vazia, não geramos o QR para não "mentir"
                if not assinatura_final:
                    return render_template_string(HTML_PAINEL, erro="O servidor respondeu vazio (Assinatura negada).")
            else:
                return render_template_string(HTML_PAINEL, erro=f"Servidor recusou (Status {resposta.status_code})")
                
        except Exception as e:
            return render_template_string(HTML_PAINEL, erro=f"Falha de Comunicação: {str(e)}")

        # 4. Montagem do Payload s:196
        payload_final = f"<q:01>s:196;u:{u_novo};i:{terminal};c:{assinatura_final};x:64;"
        
        # 5. Geração da Imagem
        img = qrcode.make(payload_final)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
        
        return render_template_string(HTML_PAINEL, payload=payload_final, qr_code=qr_b64)

    except Exception as e:
        return render_template_string(HTML_PAINEL, erro=f"Erro na Matriz: {str(e)}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

import requests
from flask import Flask, request, render_template_string
import qrcode
import io
import base64
from datetime import datetime

app = Flask(__name__)

# URL do Endpoint de Assinatura
URL_ASSINADOR = "http://35.241.41.66"

@app.route('/')
def index():
    return render_template_string(HTML_PAINEL)

@app.route('/gerar', methods=['POST'])
def gerar():
    matriz = request.form.get('matriz')
    try:
        # 1. Extração dos dados da Matriz
        u_original = matriz.split('u:')[1].split(';')[0]
        # Aqui você deve colocar o número da MÁQUINA REAL se souber, 
        # por enquanto pegamos o que vem na matriz (i:)
        terminal_real = matriz.split('i:')[1].split(';')[0] 
        dna_key_publica = matriz.split('c:')[1].split(';')[0][:32]
        
        # 2. Preparação dos Valores da Sequência
        u_novo = str(int(u_original) + 15)
        tarifa = "440" # Valor padrão da tarifa (ajuste se necessário)
        data_hora = datetime.now().strftime("%Y%m%d%H%M%S") # Data/Hora para a assinatura
        
        # 3. MONTAGEM DA SEQUÊNCIA BRUTA (A ordem que o servidor exige)
        # Sequência: Terminal -> Prefixo -> Tarifa -> Data -> Key Pública
        payload_envio = f"{terminal_real}{u_novo}{tarifa}{data_hora}{dna_key_publica}"
        
        headers = {
            'User-Agent': 'okhttp/3.12.1',
            'Content-Type': 'text/plain', # Enviando como texto bruto para o endpoint
            'Connection': 'close'
        }

        try:
            # O envio para o endpoint verificar e assinar com a Key Privada
            resposta = requests.post(URL_ASSINADOR, data=payload_envio, headers=headers, timeout=12)
            
            if resposta.status_code == 200 and resposta.text:
                assinatura_privada = resposta.text.strip()
                
                # 4. Montagem do Payload Final para o QR
                # Se o servidor devolver a assinatura, montamos o código final
                payload_final = f"<q:01>s:196;u:{u_novo};i:{terminal_real};c:{assinatura_privada};x:64;"
                
                img = qrcode.make(payload_final)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                qr_b64 = base64.b64encode(buf.getvalue()).decode()
                
                return render_template_string(HTML_PAINEL, payload=payload_final, qr_code=qr_b64)
            else:
                return render_template_string(HTML_PAINEL, erro=f"Servidor recusou a sequência (Status {resposta.status_code})")
                
        except Exception as e:
            return render_template_string(HTML_PAINEL, erro="Conexão fechada pelo servidor. Verifique a sequência de dados.")

    except Exception as e:
        return render_template_string(HTML_PAINEL, erro=f"Erro no processamento: {str(e)}")

# HTML do Painel (O mesmo estilo que você já usa)
HTML_PAINEL = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>AUTOPASS ENGINE v3.5 - PRIVATE KEY SIGNER</title>
    <style>
        body { background-color: #000; color: #0f0; font-family: monospace; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { width: 95%; max-width: 500px; border: 2px solid #0f0; padding: 20px; background: #050505; }
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

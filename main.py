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
    <title>AUTOPASS POS ENGINE v3.5</title>
    <style>
        body { font-family: 'Courier New', monospace; background: #0a0a0a; color: #00ff41; padding: 20px; text-align: center; }
        .box { max-width: 900px; margin: auto; background: #111; padding: 25px; border: 1px solid #00ff41; border-radius: 8px; box-shadow: 0 0 20px #00ff41; }
        textarea { width: 100%; height: 100px; background: #000; color: #00ff41; border: 1px solid #333; padding: 10px; margin-bottom: 20px; font-size: 12px; outline: none; }
        .btn { padding: 15px 30px; background: transparent; color: #00ff41; border: 1px solid #00ff41; font-weight: bold; cursor: pointer; text-transform: uppercase; margin: 5px; }
        .btn:hover { background: #00ff41; color: #000; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }
        .card { background: #fff; padding: 10px; border-radius: 5px; color: #000; font-size: 10px; font-weight: bold; }
        .card img { width: 100%; margin-bottom: 5px; border: 1px solid #000; }
        #status { margin: 15px 0; font-weight: bold; color: #fff; }
    </style>
</head>
<body>
    <div class="box">
        <h1>AUTOPASS POS ENGINE <small>v3.5</small></h1>
        <textarea id="mtz" placeholder="COLE A MATRIZ MÃE AQUI..."></textarea>
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
            
            document.getElementById('status').innerText = "STATUS: ENVIANDO SEQUÊNCIA AO SERVIDOR...";
            document.getElementById('grid').innerHTML = "";

            try {
                const res = await fetch('/api/injetar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ matriz, qtd })
                });
                
                const resultados = await res.json();
                
                if (!resultados || resultados.length === 0) {
                    document.getElementById('status').innerText = "ERRO: O servidor recusou a sequência ou o DNA é inválido.";
                    return;
                }

                resultados.forEach(d => {
                    const div = document.createElement('div');
                    div.className = 'card';
                    div.innerHTML = `<img src="data:image/png;base64,${d.img}"><br>U:${d.u} | X:${d.x}`;
                    document.getElementById('grid').appendChild(div);
                });
                document.getElementById('status').innerText = "STATUS: " + resultados.length + " QR(S) GERADO(S) COM SUCESSO!";
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
        # Extração dos dados mantendo os 64 primeiros caracteres do campo C
        terminal = mtz.split("i:")[1].split(";")[0]
        u_base = int(mtz.split("u:")[1].split(";")[0])
        dna_64 = mtz.split("c:")[1].split(";")[0][:64] # PRESERVA OS 64 PRIMEIROS
    except Exception as e:
        print(f"Erro ao ler matriz: {e}")
        return jsonify([])

    resultados = []
    
    for i in range(data['qtd']):
        u_novo = u_base + ((i + 1) * 15)
        ts = int(time.time())
        
        # Cálculo do Checksum X (conforme lógica de POS)
        semente = int(terminal) + u_novo + ts
        x_calc = f"{(semente % 100):02d}"
        
        # SEQUÊNCIA BRUTA: Terminal + Prefixo + Tarifa (540) + Timestamp + Checksum + DNA(64)
        payload_envio = f"{terminal}{u_novo}540{ts}{x_calc}{dna_64}"
        
        try:
            # Injeção no IP do servidor
            r = requests.post(IP_SERVIDOR, data=payload_envio, timeout=7)
            assinatura_servidor = r.text.strip()
            
            if r.status_code == 200 and assinatura_servidor:
                # MONTAGEM FINAL: Preserva o DNA_64 e concatena a nova assinatura
                payload_qr = f"<q:01>s:197;u:{u_novo};i:{terminal};c:{dna_64}{assinatura_servidor};x:{x_calc};"
                
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
            print(f"Falha na conexão: {e}")
            continue
            
    return jsonify(resultados)

if __name__ == '__main__':
    # Usando a porta 10000 para o Render
    app.run(host='0.0.0.0', port=10000)

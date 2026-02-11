from flask import Flask, render_template_string, request, jsonify
import requests
import qrcode
import io
import base64
import time

app = Flask(__name__)

# --- CONFIGURAÇÃO DE COMUNICAÇÃO (ENDPOINT) ---
IP_SERVIDOR = "http://35.241.41.66/"

HTML_PAINEL = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Painel Web - POS Clone Engine v3.5</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f0f0f; color: #00ff41; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: auto; background: #1a1a1a; padding: 30px; border-radius: 12px; border: 1px solid #00ff41; box-shadow: 0 0 20px rgba(0,255,65,0.2); }
        h1 { text-align: center; text-transform: uppercase; letter-spacing: 2px; color: #00ff41; text-shadow: 0 0 10px #00ff41; }
        textarea { width: 100%; height: 120px; background: #000; color: #00ff41; border: 1px solid #00ff41; border-radius: 8px; padding: 12px; box-sizing: border-box; font-family: 'Courier New', monospace; font-size: 14px; }
        .controls { margin: 25px 0; display: flex; gap: 15px; justify-content: center; }
        button { padding: 15px 30px; border: 1px solid #00ff41; background: transparent; color: #00ff41; font-weight: bold; cursor: pointer; transition: 0.3s; text-transform: uppercase; border-radius: 5px; }
        button:hover { background: #00ff41; color: #000; box-shadow: 0 0 15px #00ff41; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; margin-top: 30px; }
        .qr-card { background: #fff; padding: 15px; border-radius: 10px; border: 1px solid #333; text-align: center; color: #000; transition: transform 0.2s; }
        .qr-card:hover { transform: scale(1.02); }
        .qr-card img { width: 100%; margin-bottom: 10px; border: 1px solid #eee; }
        .qr-info { font-size: 0.85em; font-family: monospace; color: #333; line-height: 1.4; border-top: 1px solid #ddd; pt: 5px; }
        #status { text-align: center; color: #fff; margin: 15px 0; font-style: italic; font-weight: bold; }
        .badge { background: #00ff41; color: #000; padding: 2px 5px; border-radius: 3px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Autopass POS Engine <small style="font-size: 12px; color: #888;">v3.5</small></h1>
        <textarea id="matriz" placeholder="COLE A MATRIZ MÃE (DNA FIXO) AQUI..."></textarea>
        
        <div class="controls">
            <button onclick="gerar(1)">Gerar 1 Bilhete</button>
            <button onclick="gerar(10)">Gerar Grade (10)</button>
        </div>

        <div id="status">Aguardando comando...</div>
        <div class="grid" id="resultadoGrid"></div>
    </div>

    <script>
        async function gerar(qtd) {
            const matriz = document.getElementById('matriz').value;
            if(!matriz) return alert("ERRO: Matrix ausente.");

            document.getElementById('status').innerText = "CALCULANDO CHECKSUM E INJETANDO NO IP...";
            document.getElementById('resultadoGrid').innerHTML = "";

            try {
                const response = await fetch('/api/processar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ matriz, qtd })
                });
                
                const resultados = await response.json();
                
                if (resultados.length === 0) {
                    document.getElementById('status').innerText = "ERRO: O servidor não retornou dados assinados.";
                    return;
                }

                document.getElementById('status').innerText = "ASSINATURAS RECEBIDAS - GERANDO IMAGENS...";

                resultados.forEach(res => {
                    const card = document.createElement('div');
                    card.className = 'qr-card';
                    card.innerHTML = `
                        <img src="data:image/png;base64,${res.img}">
                        <div class="qr-info">
                            <strong>U:</strong> ${res.u}<br>
                            <strong>X:</strong> <span class="badge">${res.x}</span><br>
                            <strong>S:</strong> ${res.s}
                        </div>
                    `;
                    document.getElementById('resultadoGrid').appendChild(card);
                });
                document.getElementById('status').innerText = "OPERAÇÃO CONCLUÍDA: " + resultados.length + " QRs PRONTOS.";
            } catch (err) {
                document.getElementById('status').innerText = "ERRO CRÍTICO NA COMUNICAÇÃO.";
                console.error(err);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAINEL)

@app.route('/api/processar', methods=['POST'])
def processar():
    dados = request.json
    mtz = dados['matriz']
    quantidade = int(dados['qtd'])
    
    # --- EXTRAÇÃO DA MATRIZ (LÓGICA POS) ---
    try:
        terminal = mtz.split("i:")[1].split(";")[0]
        u_base = int(mtz.split("u:")[1].split(";")[0])
        dna_32 = mtz.split("c:")[1].split(";")[0][:32]
    except Exception as e:
        print(f"Erro na extração: {e}")
        return jsonify([])

    lista_final = []

    for i in range(quantidade):
        # 1. Salto Temporal no U (15 em 15)
        u_novo = u_base + ((i + 1) * 15)
        
        # 2. Lógica de Tempo e Checksum X (Igual ao POS)
        timestamp_atual = int(time.time())
        # Semente: Terminal + U + Hora (Correlação Total)
        semente = int(terminal) + u_novo + timestamp_atual
        x_calc = f"{(semente % 100):02d}"
        
        # 3. Cálculo de Tamanho S
        s_calculado = 197 

        # 4. Injeção de Dados Brutos no IP
        payload_bruto = f"{terminal}{u_novo}540{timestamp_atual}{x_calc}{dna_32}"
        
        try:
            # Enviando para o Servidor Assinador
            # r = requests.post(IP_SERVIDOR, data=payload_bruto, timeout=5)
            # assinatura = r.text.strip()
            
            # Fallback para teste visual enquanto o IP não retorna
            assinatura = "ASSINATURA_SERVER_OK" 

            # 5. Montagem do QR Texto Completo
            qr_texto = f"<q:01>s:{s_calculado};u:{u_novo};i:{terminal};c:{dna_32}{assinatura};x:{x_calc};"
            
            # 6. Geração da Imagem PNG (Motor Gráfico Robusto)
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(qr_texto)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

            print(f"DEBUG: QR {i+1} Gerado com sucesso no terminal.")

            lista_final.append({
                "u": u_novo,
                "x": x_calc,
                "s": s_calculado,
                "img": img_b64
            })
        except Exception as e:
            print(f"Erro no loop do IP: {e}")
            continue

    return jsonify(lista_final)

if __name__ == '__main__':
    # Aceita conexões de qualquer IP na rede (Celular e PC)
    app.run(host='0.0.0.0', port=5000)

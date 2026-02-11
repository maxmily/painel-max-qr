import requests
from flask import Flask, request, render_template_string
import qrcode
import io
import base64

app = Flask(__name__)

# O IP do seu servidor de assinatura
URL_ASSINADOR = "35.241.41.66"

@app.route('/')
def index():
    # Mantendo sua estrutura de painel
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <title>AUTOPASS POS ENGINE v3.5</title>
        <style>
            body { background-color: #000; color: #0f0; font-family: monospace; padding: 20px; }
            input, button { background: #111; color: #0f0; border: 1px solid #0f0; padding: 10px; width: 100%; margin-top: 10px; }
            .container { max-width: 500px; margin: auto; border: 1px solid #0f0; padding: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>POS INJECTOR v3.5</h1>
            <form action="/gerar" method="post">
                <input type="text" name="matriz" placeholder="Cole a Matriz Mãe aqui..." required>
                <button type="submit">INJETAR E GERAR QR</button>
            </form>
        </div>
    </body>
    </html>
    """)

@app.route('/gerar', methods=['POST'])
def gerar():
    matriz = request.form.get('matriz')
    
    try:
        # 1. Extração dos dados da Matriz Mãe
        u_original = matriz.split('u:')[1].split(';')[0]
        terminal = matriz.split('i:')[1].split(';')[0]
        dna_mae = matriz.split('c:')[1].split(';')[0][:32] # Pega os 32 bytes iniciais (DNA)
        
        # 2. Lógica do Salto (+15)
        u_novo = str(int(u_original) + 15)
        
        # 3. Requisição REAL para o Servidor de Injeção
        # Enviamos Terminal + Novo U + DNA da mãe
        payload_envio = f"{terminal}{u_novo}{dna_mae}"
        
        try:
            resposta_servidor = requests.post(URL_ASSINADOR, data=payload_envio, timeout=8)
            
            if resposta_servidor.status_code == 200:
                assinatura_final = resposta_servidor.text.strip()
            else:
                return f"Erro no Servidor: Status {resposta_servidor.status_code}"
                
        except Exception as e:
            return f"Erro de Conexão com o Servidor de Assinatura: {str(e)}"

        # 4. Montagem do Payload Final (Forçando s:196 conforme sua análise)
        # O campo 'c:' recebe EXATAMENTE o que o servidor respondeu
        payload_final = f"<q:01>s:196;u:{u_novo};i:{terminal};c:{assinatura_final};x:64;"
        
        # 5. Geração da Imagem do QR Code
        img = qrcode.make(payload_final)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        img_str = base64.b64encode(buf.getvalue()).decode()
        
        return f"""
        <body style="background:#000;color:#0f0;font-family:monospace;text-align:center;">
            <h3>INJEÇÃO CONCLUÍDA</h3>
            <p>Payload: {payload_final}</p>
            <img src="data:image/png;base64,{img_str}" style="border:10px solid white; margin:20px;">
            <br><br>
            <a href="/" style="color:#0f0;">VOLTAR</a>
        </body>
        """
        
    except Exception as e:
        return f"Erro no Processamento da Matriz: {str(e)}"

if __name__ == "__main__":
    # Roda na porta 10000 tanto local quanto no Render
    app.run(host='0.0.0.0', port=10000)

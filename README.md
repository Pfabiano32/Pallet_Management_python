# 🚀 PalletTrack – Sistema de Gerenciamento de Pallets com Firebase em Tempo Real

Biblioteca Kivy: [![Kivy](https://img.shields.io/badge/Kivy-2.2.0-blue)](https://kivy.org)
Banco de dados Firebase: [![Firebase](https://img.shields.io/badge/Firebase-Cloud%20Firestore-orange)](https://firebase.google.com)

## 🧾 Sobre o Projeto
Um sistema completo para gestão de entrada/saída de pallets com integração em tempo real usando Firebase Firestore.

![Menu do Aplicativo](menu_imagem.png)

## 📚 Índice

- 🧾 Sobre o Projeto

- ✨ Funcionalidades Principais

- 🛠 Tecnologias Utilizadas

- ⚙️ Pré-requisitos

- 🚀 Instalação

- ⚠️ Segurança de Chaves

- ▶️ Executando a Aplicação

- 📦 Empacotamento para Android

- 📂 Estrutura do Projeto

## ✨ Funcionalidades Principais

- 📦 Registro de entrada/saída de pallets

- 🔄 Sincronização em tempo real com Firebase

- 👥 Gerenciamento de clientes e seus pallets

- 📊 Consulta dos dados de registro

- 📱 Interface responsiva para desktop/mobile

- 🔒 Autenticação e segurança de dados

## 🛠 Tecnologias Utilizadas

- **Frontend e Backend**: Kivy (Python)

- **Banco de Dados**: Firebase Firestore

- **Bibliotecas Principais**:
  - `firebase-admin`: Integração com Firebase

  - `kivy`: Interface gráfica

  - `kivymd`: Componentes Material Design

## ⚙️ Pré-requisitos

- Python 3.8+
- Conta no Firebase
- Arquivo `serviceAccountKey.json` (não versionado)

## 🚀 Instalação

1. **Clone o repositório:**

    - git clone:  https://github.com/Pfabiano32/Pallet-Management_python.git

    - cd pallet-management_python

2. **Crie e ative o ambiente virtual (recomendado):**

    - python -m venv venv
source venv/bin/activate  # Linux/Mac

    - venv\Scripts\activate  # Windows

3. **Instale as dependências:**

    - pip install -r requirements.txt

4. **Configure o Firebase:**

    - No Firebase Console, crie um projeto e gere o serviceAccountKey.json

    - Coloque o arquivo na raiz do projeto

## ⚠️ Segurança de Chaves

- Nunca commit o arquivo serviceAccountKey.json! Adicione ao .gitignore:

    
    echo "serviceAccountKey.json" >> .gitignore

## 🔑 Exemplo de Arquivo serviceAccountKey.json
⚠️ **Atenção:** O arquivo serviceAccountKey.json contém credenciais sensíveis do Firebase e não deve ser enviado ao repositório.

Use o exemplo abaixo como modelo para criar o seu próprio recriar o projeto.

Exemplo de estrutura (use serviceAccountKey.example.json como modelo):

    {  "type": "service_account",
        "project_id": "nome-do-seu-projeto-firebase",
        "private_key_id": "exemplo1234567890abcdef",
        "private_key": "-----BEGIN PRIVATE KEY-----\\nSUA-CHAVE-AQUI\\n-----END PRIVATE KEY-----\\n",
        "client_email": "firebase-adminsdk-abcde@nome-do-seu-projeto-firebase.iam.gserviceaccount.com",
        "client_id": "123456789012345678901",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-abcde%40nome-do-seu-projeto-firebase.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"

        }

## ▶️ Executando a Aplicação

main.py

## 📦 Empacotamento para Android

1. **Instale o Buildozer:**

    - pip install buildozer

2. **Crie o arquivo de especificação:**

    - buildozer init

3. **Edite o buildozer.spec:**

    - requirements = python3, kivy==2.2.0, firebase-admin

    - android.permissions = INTERNET

4. Construa o APK:

    - buildozer -v android debug

## 📂 Arquivo 'requirements.txt'

kivy == 2.2.0

firebase-admin == 6.2.0

Python == 13.13.3

## 🛠 Estrutura do Projeto

    pallet-management/

    ├── main.py

    ├── pallet.kv

    ├── serviceAccountKey.json  # Não versionar!

    ├── requirements.txt

    ├── buildozer.spec          # Para empacotamento Android

    └── fonts/
    
        └── fa-solid-900.otf    # Font Awesome

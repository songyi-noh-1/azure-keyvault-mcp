# Azure Key Vault 관리 Agent (MCP)

**Azure Key Vault의 Secret 및 Certificate 관리, Application Gateway SSL 인증서 관리 전문 MCP 서버**

## 🎯 이 Agent가 하는 일

### ✅ 전문 분야

- **Secret 관리**
  - Secret 등록/조회/목록/삭제
  - Secret 버전 관리

- **Certificate 관리**
  - 인증서 등록 (PFX, PEM, CRT 등 모든 형식 지원)
  - 인증서 형식 자동 변환 (PEM/CRT → PFX)
  - 인증서 체인 import
  - 인증서 조회/목록/삭제
  - **신규 인증서 추가 시 Application Gateway 등록 제안**

- **Application Gateway 관리**
  - Application Gateway 목록 조회
  - Application Gateway 상세 정보 조회
  - Key Vault 인증서를 Application Gateway SSL 인증서로 등록
  - Application Gateway SSL 인증서 목록 조회
  - Application Gateway SSL 인증서 제거

- **인증 관리**
  - Azure CLI 인증 자동 체크
  - Key Vault 목록 조회 및 선택

### ❌ 이 Agent가 하지 않는 일

- App Service 배포
- Virtual Machine 관리
- 네트워크 설정
- Storage 관리
- 기타 Azure 리소스 관리

→ **Key Vault Secret/Certificate 관리 및 Application Gateway SSL 인증서 관리**를 전문으로 다룹니다.

## 💬 사용 예시

### 인증서 교체

```
You: ssl 인증서 교체가 필요해

AI: ✅ 인증 완료
📋 Key Vault 목록: 
1. kv-prod-01
2. kv-test-01

어느 Key Vault인가요? 

You: kv-prod-01

AI: ✅ kv-prod-01 선택됨
📋 현재 인증서:
1. ssl-cert-2024 (만료: 2025-06-30)
2. api-cert (만료: 2025-12-31)

어떤 인증서를 교체하시겠어요?

You: ssl-cert-2024

AI: 새 인증서 파일 형식이 무엇인가요?  (PFX/PEM/CRT)

You: PFX 파일 있어

AI: PFX 파일을 base64로 인코딩해주세요: 
```bash
base64 -i new-cert.pfx | pbcopy
```
그리고 붙여넣어 주세요. 
비밀번호도 알려주세요.

You: [base64 내용], 비밀번호는 "pass123"

AI: ✅ 인증서 'ssl-cert-2024' 교체 완료! 
Thumbprint: a1b2c3d4... 
만료일: 2026-12-31
```

### Secret 조회

```
You: db-password secret 값 알려줘

AI: [자동으로 Key Vault 선택되어 있다면]
🔐 Secret 'db-password'
값: MySecretPassword123
버전: abc123
수정일: 2025-12-09
```

### 빠른 등록

```
You: kv-prod의 "api-key"로 "xyz789" secret 등록해줘

AI: [select_keyvault 자동 실행]
[set_secret 자동 실행]
✅ Secret 'api-key' 저장 완료
버전: def456
```

### 여러 Secret 한 번에 등록

```
You: 다음 secret들을 한 번에 등록해줘:
- db-connection-string: "Server=..."
- api-key: "abc123"
- jwt-secret: "secret-key"

AI: [select_keyvault 자동 실행]
[set_secrets 자동 실행]
✅ 여러 Secret 등록 결과

전체: 3개
성공: 3개 ✅
실패: 0개 ❌

성공한 Secret:
- ✅ db-connection-string (버전: v1)
- ✅ api-key (버전: v1)
- ✅ jwt-secret (버전: v1)
```

### 신규 인증서 추가 및 Application Gateway 등록

```
You: 새로운 SSL 인증서를 Key Vault에 등록해줘

AI: ✅ 인증서 'new-ssl-cert' import 완료
Thumbprint: a1b2c3d4...

💡 이 인증서를 Application Gateway의 SSL 인증서로도 등록하시겠어요?
`add_ssl_certificate_to_appgw` 도구를 사용하여 등록할 수 있습니다.

You: 응, 등록해줘

AI: ✅ SSL 인증서 added 완료
- 인증서 이름: new-ssl-cert
- Key Vault 인증서: new-ssl-cert
- Key Vault: kv-prod-01

💡 Application Gateway의 Listener TLS certificates에 등록되었습니다.
🔄 Key Vault에서 인증서가 갱신되면 Application Gateway도 자동으로 최신 버전을 사용합니다.
```

### Application Gateway SSL 인증서 관리

```
You: appgw에 등록된 TLS 인증서 목록 알려줘

AI: 📋 총 2개의 SSL 인증서:
- tempkey
  - Key Vault Secret ID: https://kv-prod-01.vault.azure.net:443/secrets/tempkey/
  - Provisioning State: Succeeded
```

## 📋 사전작업 (MCP 서버 설정 전 필수)

> ⚠️ **중요:** MCP 서버를 설정하기 전에 아래 사전작업을 모두 완료해야 합니다.

### 1. Python 설치 확인

**macOS/Linux:**
```bash
python3 --version
# Python 3.8 이상이 필요합니다
```

**Windows:**
```powershell
python --version
# Python 3.8 이상이 필요합니다
```

> **참고:** 
> - Python이 설치되어 있지 않다면 [Python 공식 사이트](https://www.python.org/downloads/)에서 다운로드하세요.
> - Windows에서 Python 설치 시 **"Add Python to PATH"** 옵션을 체크하는 것을 권장합니다.
> - `python` 명령이 작동하지 않으면 `py` 명령을 시도해보세요.

### 2. Azure CLI 설치 및 로그인

**Azure CLI 설치 확인:**
```bash
az --version
```

> Azure CLI가 설치되어 있지 않다면:
> - **macOS:** `brew install azure-cli`
> - **Linux:** [Azure CLI 설치 가이드](https://learn.microsoft.com/cli/azure/install-azure-cli)
> - **Windows:** [Azure CLI 설치 가이드](https://learn.microsoft.com/cli/azure/install-azure-cli-windows)

**Azure 로그인:**
```bash
az login
```

> 로그인 후 구독이 올바르게 설정되었는지 확인:
> ```bash
> az account show
> ```

### 3. 프로젝트 클론 및 환경 설정

**macOS/Linux:**
```bash
git clone https://github.com/songyi-noh/azure-keyvault-mcp.git
cd azure-keyvault-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```powershell
# 1단계: 프로젝트 클론
git clone https://github.com/songyi-noh/azure-keyvault-mcp.git
cd azure-keyvault-mcp

# 2단계: venv 생성 (프로젝트 폴더 안에 생성됨)
python -m venv venv

# 3단계: venv 활성화
venv\Scripts\activate

# 4단계: 필요한 패키지 설치
pip install -r requirements.txt
```

> **참고:**
> - venv 활성화되면 프롬프트 앞에 `(venv)`가 표시됩니다.
> - 이 명령을 실행하면 `azure-keyvault-mcp\venv\` 폴더가 생성됩니다.

### ✅ 사전작업 완료 확인

모든 사전작업이 완료되었는지 확인:

```bash
# Python 버전 확인
python3 --version  # 또는 python --version (Windows)

# Azure CLI 로그인 확인
az account show

# venv 활성화 확인 (프롬프트에 (venv) 표시)
# 패키지 설치 확인
pip list | grep azure
```

위 명령들이 모두 정상적으로 실행되면 다음 단계인 **"⚙️ MCP 서버 설정"**으로 진행하세요.

## ⚙️ MCP 서버 설정

> ⚠️ **중요:** 아래 설정을 진행하기 전에 **"📋 사전작업"** 섹션의 모든 단계를 완료했는지 확인하세요.

> **💡 venv란?**
> 
> `venv`는 **프로젝트 폴더 안에 생성되는 가상환경**입니다.
> 
> - **생성 위치:** 프로젝트 폴더 안의 `venv/` 디렉토리
> - **생성 방법:** `python3 -m venv venv` 명령으로 생성
> - **Python 경로:**
>   - macOS/Linux: `프로젝트경로/venv/bin/python`
>   - Windows: `프로젝트경로\venv\Scripts\python.exe`
> - **왜 사용하나요?** 프로젝트별로 독립적인 Python 패키지 환경을 만들어 의존성 충돌을 방지합니다
> 
> MCP 설정에서 이 venv의 Python을 사용하여 `server.py`를 실행합니다.

### Cursor 설정

```json
// ~/.cursor/mcp.json
{
  "mcpServers": {
    "azure-keyvault": {
      "command": "/절대경로/azure-keyvault-mcp/venv/bin/python",
      "args": ["/절대경로/azure-keyvault-mcp/server.py"]
    }
  }
}
```

### Claude Desktop 설정

Claude Desktop에서도 이 MCP 서버를 사용할 수 있습니다.

> **💡 프로젝트별 규칙 설정:**
> 
> Cursor의 `.cursorrules`와 비슷하게, Claude Desktop에서도 프로젝트별 규칙을 설정할 수 있습니다:
> - 프로젝트 루트에 `.claude` 파일을 생성하면 Claude Desktop이 자동으로 인식합니다
> - `.cursorrules` 파일과 동일한 내용을 `.claude` 파일로 복사하여 사용할 수 있습니다

**macOS:**

설정 파일 위치: `~/Library/Application Support/Claude/claude_desktop_config.json`

> **💡 설정 파일 빠르게 열기:**
> 
> Finder에서 설정 파일을 열려면:
> ```bash
> open -a "TextEdit" ~/Library/Application\ Support/Claude/claude_desktop_config.json
> ```
> 
> 또는 터미널에서:
> ```bash
> cd ~/Library/Application\ Support/Claude/
> # 파일이 없으면 생성
> touch claude_desktop_config.json
> # 편집
> nano claude_desktop_config.json
> ```

설정 예시:
```json
{
  "mcpServers": {
    "azure-keyvault": {
      "command": "/Users/yourname/azure-keyvault-mcp/venv/bin/python",
      "args": ["/Users/yourname/azure-keyvault-mcp/server.py"]
    }
  }
}
```

> **💡 절대 경로 빠르게 확인하기:**
> 
> 프로젝트 폴더에서 다음 명령으로 경로를 복사할 수 있습니다:
> ```bash
> cd /path/to/azure-keyvault-mcp
> echo "$(pwd)/venv/bin/python"
> echo "$(pwd)/server.py"
> ```

**Windows:**

설정 파일 위치: `%APPDATA%\Claude\claude_desktop_config.json` (보통 `C:\Users\YourName\AppData\Roaming\Claude\claude_desktop_config.json`)

> **💡 설정 파일 빠르게 열기:**
> 
> PowerShell에서:
> ```powershell
> # 설정 파일 경로 확인
> $configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
> Write-Host "설정 파일: $configPath"
> 
> # 디렉토리 생성 (없는 경우)
> New-Item -ItemType Directory -Force -Path "$env:APPDATA\Claude"
> 
> # 메모장으로 열기
> notepad $configPath
> ```

설정 예시:
```json
{
  "mcpServers": {
    "azure-keyvault": {
      "command": "C:/Users/YourName/azure-keyvault-mcp/venv/Scripts/python.exe",
      "args": ["C:/Users/YourName/azure-keyvault-mcp/server.py"]
    }
  }
}
```

> **💡 Windows에서 슬래시(`/`) 사용 권장:**
> 
> Windows에서도 슬래시를 사용할 수 있으며, 백슬래시 이스케이프 문제를 피할 수 있습니다.

> **💡 Windows에서 경로 찾는 방법:**
> 
> 1. **PowerShell에서 경로 확인:**
>    ```powershell
>    cd C:\Users\YourName\azure-keyvault-mcp
>    (Get-Location).Path
>    ```
> 
> 2. **또는 파일 탐색기에서:**
>    - 프로젝트 폴더를 열고 주소창을 클릭하면 전체 경로가 표시됩니다
>    - 예: `C:\Users\YourName\azure-keyvault-mcp`
> 
> 3. **설정 파일 예시 (실제 경로):**
>    ```json
>    {
>      "mcpServers": {
>        "azure-keyvault": {
>          "command": "C:\\Users\\YourName\\azure-keyvault-mcp\\venv\\Scripts\\python.exe",
>          "args": ["C:\\Users\\YourName\\azure-keyvault-mcp\\server.py"]
>        }
>      }
>    }
>    ```
> 
>    > **중요:** Windows 경로에서는 백슬래시(`\`)를 두 개(`\\`)로 이스케이프해야 합니다.

### ⚠️ Windows에서 "지정된 경로를 찾을 수 없다" 오류 해결

**문제 진단:**

1. **Python 실행 파일 경로 확인:**
   ```powershell
   # 프로젝트 폴더에서 실행
   cd C:\Users\YourName\azure-keyvault-mcp
   
   # venv의 Python이 존재하는지 확인
   Test-Path venv\Scripts\python.exe
   # True가 나와야 함
   ```

2. **server.py 파일 경로 확인:**
   ```powershell
   Test-Path server.py
   # True가 나와야 함
   ```

3. **경로에 공백이나 특수문자가 있는지 확인:**
   - 경로에 공백이 있으면 따옴표로 감싸야 할 수 있습니다
   - 예: `C:\Users\My Name\azure-keyvault-mcp` → 경로에 공백 있음

**해결 방법:**

1. **슬래시 사용 (권장):**
   ```json
   {
     "mcpServers": {
       "azure-keyvault": {
         "command": "C:/Users/YourName/azure-keyvault-mcp/venv/Scripts/python.exe",
         "args": ["C:/Users/YourName/azure-keyvault-mcp/server.py"]
       }
     }
   }
   ```
   > Windows에서도 슬래시(`/`)를 사용할 수 있습니다!

2. **경로에 공백이 있는 경우:**
   ```json
   {
     "mcpServers": {
       "azure-keyvault": {
         "command": "\"C:/Users/My Name/azure-keyvault-mcp/venv/Scripts/python.exe\"",
         "args": ["C:/Users/My Name/azure-keyvault-mcp/server.py"]
       }
     }
   }
   ```

3. **venv가 제대로 생성되었는지 확인:**
   ```powershell
   # venv 재생성
   Remove-Item -Recurse -Force venv
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **절대 경로 대신 상대 경로 사용 (프로젝트 폴더 기준):**
   ```json
   {
     "mcpServers": {
       "azure-keyvault": {
         "command": "python",
         "args": ["-m", "venv", "venv", "&&", "venv\\Scripts\\python.exe", "server.py"]
       }
     }
   }
   ```
   > 이 방법은 작동하지 않을 수 있으므로 **절대 경로 사용을 권장**합니다.

**가장 확실한 방법:**

PowerShell에서 다음 명령으로 정확한 경로를 복사하세요:
```powershell
cd C:\Users\YourName\azure-keyvault-mcp
$pythonPath = (Resolve-Path "venv\Scripts\python.exe").Path
$serverPath = (Resolve-Path "server.py").Path
Write-Host "Python: $pythonPath"
Write-Host "Server: $serverPath"
```

출력된 경로를 그대로 설정 파일에 복사하되, 백슬래시를 슬래시로 변경하거나 `\\`로 이스케이프하세요.

**Linux:**

설정 파일 위치: `~/.config/Claude/claude_desktop_config.json`

> **💡 설정 파일 빠르게 열기:**
> ```bash
> # 디렉토리 생성 (없는 경우)
> mkdir -p ~/.config/Claude
> # 파일 편집
> nano ~/.config/Claude/claude_desktop_config.json
> ```

설정 예시:
```json
{
  "mcpServers": {
    "azure-keyvault": {
      "command": "/home/username/azure-keyvault-mcp/venv/bin/python",
      "args": ["/home/username/azure-keyvault-mcp/server.py"]
    }
  }
}
```

> **참고:** 설정 파일을 수정한 후 Claude Desktop을 재시작해야 합니다.

### 🔍 Claude Desktop 설정 확인 및 테스트

#### 1. 설정 파일 경로 빠르게 찾기

**macOS:**
```bash
# 설정 파일 경로 확인
echo ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 설정 파일 편집
open -a "TextEdit" ~/Library/Application\ Support/Claude/claude_desktop_config.json
# 또는
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```powershell
# 설정 파일 경로 확인
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
Write-Host $configPath

# 설정 파일 편집 (메모장으로 열기)
notepad $configPath
```

**Linux:**
```bash
# 설정 파일 경로 확인
echo ~/.config/Claude/claude_desktop_config.json

# 설정 파일 편집
nano ~/.config/Claude/claude_desktop_config.json
```

#### 2. 설정 파일이 올바른지 확인

설정 파일이 올바른 JSON 형식인지 확인하세요:

**macOS/Linux:**
```bash
# JSON 유효성 검사
python3 -m json.tool ~/Library/Application\ Support/Claude/claude_desktop_config.json
# 또는 (Linux)
python3 -m json.tool ~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```powershell
# JSON 유효성 검사
python -m json.tool "$env:APPDATA\Claude\claude_desktop_config.json"
```

#### 3. MCP 서버 수동 테스트

설정이 올바른지 확인하기 위해 MCP 서버를 직접 실행해볼 수 있습니다:

```bash
# 프로젝트 폴더로 이동
cd /절대경로/azure-keyvault-mcp

# venv 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# MCP 서버가 정상적으로 시작되는지 확인 (stdio 모드로 실행)
python server.py
```

> ⚠️ **참고:** MCP 서버는 stdio 모드로 실행되므로, 직접 실행하면 대화형 입력을 기다립니다. 이것은 정상적인 동작입니다. `Ctrl+C`로 종료할 수 있습니다.

#### 4. Claude Desktop에서 MCP 서버 확인

1. **Claude Desktop 재시작**
   - 설정 파일을 수정한 후 반드시 Claude Desktop을 완전히 종료하고 다시 시작하세요.

2. **MCP 서버 상태 확인**
   - Claude Desktop을 열고 새 대화를 시작합니다.
   - Claude에게 "Azure 인증 상태 확인해줘"라고 요청합니다.
   - MCP 서버가 정상적으로 연결되었다면 `check_azure_auth` 도구가 사용됩니다.

3. **도구 목록 확인**
   - Claude Desktop의 개발자 도구나 로그에서 MCP 서버가 등록되었는지 확인할 수 있습니다.
   - 또는 "Azure Key Vault에서 사용 가능한 도구 목록을 보여줘"라고 요청해보세요.

#### 5. 환경 변수 설정 (필요한 경우)

특정 상황에서 환경 변수가 필요할 수 있습니다. Claude Desktop 설정 파일에서 환경 변수를 추가할 수 있습니다:

**macOS/Linux:**
```json
{
  "mcpServers": {
    "azure-keyvault": {
      "command": "/절대경로/azure-keyvault-mcp/venv/bin/python",
      "args": ["/절대경로/azure-keyvault-mcp/server.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "AZURE_KEYVAULT_DISABLE_SSL_VERIFY": "0"
      }
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "azure-keyvault": {
      "command": "C:/절대경로/azure-keyvault-mcp/venv/Scripts/python.exe",
      "args": ["C:/절대경로/azure-keyvault-mcp/server.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "AZURE_KEYVAULT_DISABLE_SSL_VERIFY": "0"
      }
    }
  }
}
```

#### 6. 디버깅 및 트러블슈팅

**문제: MCP 서버가 Claude Desktop에 나타나지 않습니다**

1. **설정 파일 경로 확인**
   - 설정 파일이 올바른 위치에 있는지 확인하세요.
   - 파일 이름이 정확히 `claude_desktop_config.json`인지 확인하세요.

2. **JSON 형식 확인**
   - 설정 파일이 유효한 JSON인지 확인하세요.
   - 쉼표(`,`)나 따옴표(`"`)가 빠지지 않았는지 확인하세요.

3. **경로 확인**
   - Python 실행 파일 경로와 `server.py` 경로가 정확한지 확인하세요.
   - 절대 경로를 사용하는 것을 권장합니다.

4. **Claude Desktop 재시작**
   - 설정 파일을 수정한 후 Claude Desktop을 완전히 종료하고 다시 시작하세요.
   - macOS의 경우 Activity Monitor에서 Claude Desktop 프로세스를 확인하세요.

**문제: MCP 서버는 나타나지만 도구가 작동하지 않습니다**

1. **Azure 인증 확인**
   - 터미널에서 `az account show`를 실행하여 Azure CLI 로그인 상태를 확인하세요.
   - 로그인이 되어 있지 않다면 `az login`을 실행하세요.

2. **MCP 서버 로그 확인**
   - Claude Desktop의 개발자 도구나 콘솔에서 오류 메시지를 확인하세요.
   - 또는 터미널에서 직접 MCP 서버를 실행하여 오류를 확인할 수 있습니다.

**문제: 경로에 공백이나 특수문자가 있는 경우**

경로에 공백이 있거나 특수문자가 있는 경우, 따옴표로 감싸거나 슬래시(`/`)를 사용하세요:

```json
{
  "mcpServers": {
    "azure-keyvault": {
      "command": "/Users/My Name/azure-keyvault-mcp/venv/bin/python",
      "args": ["/Users/My Name/azure-keyvault-mcp/server.py"]
    }
  }
}
```

또는 Windows에서는:

```json
{
  "mcpServers": {
    "azure-keyvault": {
      "command": "C:/Users/My Name/azure-keyvault-mcp/venv/Scripts/python.exe",
      "args": ["C:/Users/My Name/azure-keyvault-mcp/server.py"]
    }
  }
}
```

#### 7. 빠른 설정 스크립트 (선택사항)

프로젝트 폴더에서 실행하여 설정 파일 경로와 예시를 출력하는 스크립트를 만들 수 있습니다:

**macOS/Linux (`setup_claude_desktop.sh`):**
```bash
#!/bin/bash
PROJECT_DIR=$(pwd)
PYTHON_PATH="$PROJECT_DIR/venv/bin/python"
SERVER_PATH="$PROJECT_DIR/server.py"

echo "📋 Claude Desktop 설정 정보:"
echo ""
echo "설정 파일 위치:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_PATH="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    echo "  $CONFIG_PATH"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    CONFIG_PATH="$HOME/.config/Claude/claude_desktop_config.json"
    echo "  $CONFIG_PATH"
fi
echo ""
echo "설정 예시:"
cat <<EOF
{
  "mcpServers": {
    "azure-keyvault": {
      "command": "$PYTHON_PATH",
      "args": ["$SERVER_PATH"]
    }
  }
}
EOF
```

**Windows (`setup_claude_desktop.ps1`):**
```powershell
$projectDir = (Get-Location).Path
$pythonPath = Join-Path $projectDir "venv\Scripts\python.exe"
$serverPath = Join-Path $projectDir "server.py"
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"

Write-Host "📋 Claude Desktop 설정 정보:" -ForegroundColor Cyan
Write-Host ""
Write-Host "설정 파일 위치:"
Write-Host "  $configPath"
Write-Host ""
Write-Host "설정 예시:"
$config = @{
    mcpServers = @{
        "azure-keyvault" = @{
            command = $pythonPath
            args = @($serverPath)
        }
    }
}
$config | ConvertTo-Json -Depth 10
```

## 🛠️ 지원 도구

| 카테고리 | 도구 | 설명 |
|---------|------|------|
| **인증** | check_azure_auth | Azure 인증 상태 확인 |
| **Key Vault** | list_keyvaults | Key Vault 목록 조회 |
| | select_keyvault | Key Vault 선택 |
| **Secret** | set_secret | Secret 등록/업데이트 |
| | set_secrets | 여러 개의 Secret을 한 번에 등록/업데이트 |
| | get_secret | Secret 조회 |
| | list_secrets | Secret 목록 |
| | delete_secret | Secret 삭제 |
| **Certificate** | import_certificate_from_pfx | PFX 인증서 import |
| | convert_pem_to_pfx_and_import | PEM → PFX 변환 후 import |
| | import_crt_certificate | CRT → PFX 변환 후 import |
| | import_bundle_certificate | 번들 PEM → PFX |
| | import_certificate_with_chain | 체인 포함 import |
| | import_certificate_from_files | 로컬 파일 경로로부터 import (PEM, CRT, PFX 지원) |
| | import_pfx_from_file | 로컬 PFX 파일로부터 직접 import |
| | decode_and_import_certificate | 파일 내용(텍스트/base64) 자동 감지 후 import |
| | import_certificate_with_auto_chain | 파일 기반 인증서 import (체인 자동 감지) |
| | get_certificate | 인증서 조회 |
| | list_certificates | 인증서 목록 |
| | delete_certificate | 인증서 삭제 |
| | detect_certificate_format | 인증서 형식 감지 |
| **Application Gateway** | list_application_gateways | Application Gateway 목록 조회 |
| | get_application_gateway | Application Gateway 상세 정보 조회 |
| | add_ssl_certificate_to_appgw | Key Vault 인증서를 Application Gateway SSL 인증서로 추가 |
| | list_appgw_ssl_certificates | Application Gateway SSL 인증서 목록 조회 |
| | remove_ssl_certificate_from_appgw | Application Gateway에서 SSL 인증서 제거 |




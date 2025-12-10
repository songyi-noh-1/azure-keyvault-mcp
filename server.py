# server.py
import asyncio
import os
import sys
import json
import base64
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from azure_auth import AzureAuthManager
from keyvault_manager import KeyVaultManager
from cert_utils import CertificateUtils

# ⭐ 자동 로그인 시도 안 함 (상태만 체크)
auth_manager = AzureAuthManager(auto_login=False)

# Key Vault URI (환경 변수 또는 동적 선택)
KEYVAULT_URI = os.environ.get("KEYVAULT_URI")

# Key Vault Manager (인증 성공 시에만 초기화)
kv_manager = None
if auth_manager.is_authenticated and KEYVAULT_URI: 
    try:
        kv_manager = KeyVaultManager(KEYVAULT_URI, auth_manager.get_credential())
    except Exception as e:
        print(f"⚠️ Key Vault 초기화 실패: {e}", file=sys.stderr)

server = Server("azure-keyvault")

@server.list_tools()
async def handle_list_tools():
    return [
        # ===== 인증 관리 =====
        Tool(
            name="check_azure_auth",
            description="Azure 인증 상태 확인",
            inputSchema={"type": "object", "properties": {}}
        ),
        
        # ===== Key Vault 선택 =====
        Tool(
            name="list_keyvaults",
            description="현재 구독의 모든 Key Vault 목록 조회",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="select_keyvault",
            description="작업할 Key Vault 선택",
            inputSchema={
                "type": "object",
                "properties": {
                    "vault_name": {"type": "string", "description": "Key Vault 이름"}
                },
                "required": ["vault_name"]
            }
        ),
        
        # Secret 관리
        Tool(
            name="set_secret",
            description="Key Vault에 secret 등록/업데이트",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Secret 이름"},
                    "value": {"type": "string", "description": "Secret 값"}
                },
                "required": ["name", "value"]
            }
        ),
        Tool(
            name="get_secret",
            description="Key Vault에서 secret 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Secret 이름"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="list_secrets",
            description="Key Vault의 모든 secret 목록 조회",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="delete_secret",
            description="Key Vault에서 secret 삭제",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Secret 이름"}
                },
                "required": ["name"]
            }
        ),
        
        # Certificate 관리
        Tool(
            name="import_certificate_from_pfx",
            description="PFX 파일로부터 인증서를 Key Vault에 등록",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "인증서 이름"},
                    "pfx_base64": {"type": "string", "description": "PFX 파일 내용 (base64 인코딩)"},
                    "password": {"type": "string", "description": "PFX 비밀번호 (옵션)"}
                },
                "required": ["name", "pfx_base64"]
            }
        ),
        Tool(
            name="convert_pem_to_pfx_and_import",
            description="PEM 형식 인증서를 PFX로 변환 후 Key Vault에 등록",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "인증서 이름"},
                    "cert_pem_base64": {"type": "string", "description": "인증서 PEM (base64)"},
                    "key_pem_base64": {"type": "string", "description": "개인키 PEM (base64)"},
                    "password": {"type": "string", "description": "PFX 비밀번호 (옵션)"}
                },
                "required": ["name", "cert_pem_base64", "key_pem_base64"]
            }
        ),
        Tool(
            name="generate_self_signed_cert",
            description="자체 서명 인증서 생성 후 Key Vault에 등록 (테스트용)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "인증서 이름"},
                    "common_name": {"type": "string", "description": "CN (Common Name)"},
                    "password": {"type": "string", "description": "비밀번호 (옵션)"}
                },
                "required": ["name", "common_name"]
            }
        ),
        Tool(
            name="get_certificate",
            description="Key Vault에서 인증서 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "인증서 이름"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="list_certificates",
            description="Key Vault의 모든 인증서 목록 조회",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="delete_certificate",
            description="Key Vault에서 인증서 삭제",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "인증서 이름"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="import_crt_certificate",
            description="CRT/CER 형식 인증서를 PFX로 변환 후 Key Vault에 등록",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "인증서 이름"},
                    "cert_crt_base64": {"type": "string", "description": "CRT/CER 파일 (base64)"},
                    "key_base64": {"type": "string", "description": "개인키 파일 (base64)"},
                    "password": {"type": "string", "description": "PFX 비밀번호 (옵션)"}
                },
                "required": ["name", "cert_crt_base64", "key_base64"]
            }
        ),
        
        Tool(
            name="import_bundle_certificate",
            description="번들 PEM 파일 (cert+key 하나의 파일)을 PFX로 변환 후 등록",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "인증서 이름"},
                    "bundle_pem_base64": {"type": "string", "description": "번들 PEM (base64)"},
                    "password": {"type": "string", "description": "PFX 비밀번호 (옵션)"}
                },
                "required": ["name", "bundle_pem_base64"]
            }
        ),
        
        Tool(
            name="import_certificate_with_chain",
            description="인증서 + 중간 인증서 체인을 PFX로 변환 후 등록",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "인증서 이름"},
                    "cert_base64": {"type": "string", "description": "주 인증서 (base64)"},
                    "key_base64": {"type": "string", "description": "개인키 (base64)"},
                    "chain_base64_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "중간 인증서 목록 (각각 base64)"
                    },
                    "password": {"type": "string", "description": "PFX 비밀번호 (옵션)"}
                },
                "required": ["name", "cert_base64", "key_base64"]
            }
        ),
        
        Tool(
            name="detect_certificate_format",
            description="인증서 파일의 형식 감지 (PEM/DER/CRT)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cert_base64": {"type": "string", "description": "인증서 파일 (base64)"}
                },
                "required": ["cert_base64"]
            }
        ),
        # server.py - @server.list_tools()에 추가

        Tool(
            name="import_certificate_from_files",
            description="로컬 파일 경로로부터 인증서를 import (PEM, CRT, PFX 지원)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Key Vault에 저장할 인증서 이름"},
                    "cert_path": {"type": "string", "description": "인증서 파일 경로 (예: /path/to/server.crt)"},
                    "key_path": {"type": "string", "description": "개인키 파일 경로 (예: /path/to/server.key, PFX는 생략)"},
                    "chain_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "중간 인증서 경로 리스트 (옵션)"
                    },
                    "password": {"type": "string", "description": "비밀번호 (옵션)"}
                },
                "required": ["name", "cert_path"]
            }
        ),

        Tool(
            name="import_pfx_from_file",
            description="로컬 PFX 파일로부터 직접 import",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Key Vault에 저장할 인증서 이름"},
                    "pfx_path": {"type": "string", "description": "PFX 파일 경로"},
                    "password": {"type":  "string", "description": "PFX 비밀번호 (옵션)"}
                },
                "required": ["name", "pfx_path"]
            }
        ),
        # server.py

        Tool(
            name="decode_and_import_certificate",
            description="Cursor에서 드래그한 파일 내용을 받아서 자동으로 형식 판단 후 import",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Key Vault에 저장할 이름"},
                    "cert_content": {"type": "string", "description": "인증서 파일 내용 (텍스트 또는 base64)"},
                    "key_content": {"type": "string", "description": "개인키 파일 내용 (옵션)"},
                    "chain_contents": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "중간 인증서 내용 리스트 (옵션)"
                    },
                    "password": {"type": "string", "description": "비밀번호 (옵션)"}
                },
                "required": ["name", "cert_content"]
            }
        ),
        
        Tool(
            name="import_certificate_with_auto_chain",
            description="인증서 파일(crt/pem)과 키 파일을 받아서 자동으로 형식 판단 후 PFX로 변환하여 import. 체인 인증서가 같은 디렉토리에 여러 파일로 분리되어 있을 경우 자동으로 찾아서 합쳐서 처리",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Key Vault에 저장할 인증서 이름"},
                    "cert_path": {"type": "string", "description": "인증서 파일 경로 (예: /path/to/server.crt 또는 server.pem)"},
                    "key_path": {"type": "string", "description": "개인키 파일 경로 (예: /path/to/server.key)"},
                    "chain_directory": {"type": "string", "description": "체인 인증서가 있는 디렉토리 경로 (옵션, 지정하지 않으면 cert_path와 같은 디렉토리에서 자동 검색)"},
                    "chain_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "체인 인증서 파일 이름 패턴 (옵션, 예: ['chain*.crt', 'intermediate*.pem']). 지정하지 않으면 자동으로 감지"
                    },
                    "password": {"type": "string", "description": "PFX 비밀번호 (옵션)"}
                },
                "required": ["name", "cert_path", "key_path"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    global kv_manager, KEYVAULT_URI
    
    try:
        # ===== ⭐ 모든 도구 실행 전에 인증 체크 (자동) =====
        
        # check_azure_auth 도구는 예외 (무한 루프 방지)
        if name == "check_azure_auth":
            # 현재 상태 재확인 (중요!)
            # force_check=True로 실제로 az account show를 실행
            auth_manager.refresh_auth_status(force_check=True)
            
            status = auth_manager.get_auth_status()
            
            if status["authenticated"]:
                sub = status["subscription"]
                result = f"✅ Azure 인증 완료\n\n"
                if sub:
                    result += f"**구독 정보:**\n"
                    result += f"- 이름: {sub.get('name', 'N/A')}\n"
                    result += f"- ID: {sub.get('id', 'N/A')[:20]}...\n"
                    result += f"- 테넌트: {sub.get('tenantId', 'N/A')[:20]}...\n"
                return [TextContent(type="text", text=result)]
            else:
                result = f"❌ Azure 인증 필요\n\n"
                result += f"**문제:** {status['message']}\n\n"
                result += f"**해결 방법:**\n"
                
                if "Azure CLI가 설치되지" in status['message']:
                    result += "1. Azure CLI 설치\n"
                    result += "2. 설치 후:  `az login`\n"
                elif "로그인되어 있지" in status['message']:
                    result += "1. 터미널에서:  `az login`\n"
                    result += "2. 브라우저에서 로그인\n"
                    result += "3. 로그인 완료 후 **이 메시지에 '로그인 완료'라고 답변**해주세요\n"
                
                return [TextContent(type="text", text=result)]
        
        # ===== ⭐ 다른 모든 도구 - 인증 체크 시 재확인 =====
        if name != "check_azure_auth": 
            # 인증 안 되어 있으면 재확인 시도
            if not auth_manager.is_authenticated:
                # 한 번 더 체크 (사용자가 로그인했을 수 있음)
                # force_check=False로 이미 인증된 경우 빠른 경로 사용
                auth_manager.refresh_auth_status(force_check=False)
                
                # 여전히 안 되어 있으면 안내
                if not auth_manager.is_authenticated:
                    status = auth_manager.get_auth_status()
                    result = f"❌ Azure 인증 필요\n\n"
                    result += f"**문제:** {status['message']}\n\n"
                    result += f"**해결 방법:**\n"
                    result += "1. 터미널에서: `az login`\n"
                    result += "2. 브라우저에서 로그인\n"
                    result += "3. 로그인 완료 후 **'인증 확인'** 또는 **'로그인 완료'**라고 말씀해주세요\n"
                    
                    return [TextContent(type="text", text=result)]
        
        # === Key Vault 선택 ===
        if name == "list_keyvaults":
            vaults = auth_manager.list_keyvaults()
            if not vaults: 
                result = "❌ Key Vault를 찾을 수 없습니다.\n\n"
                result += "**가능한 원인:**\n"
                result += "1. 현재 구독에 Key Vault가 없음\n"
                result += "2. Key Vault 읽기 권한이 없음\n\n"
                result += "**확인 방법:**\n"
                result += "```bash\n"
                result += "# 현재 구독 확인\n"
                result += "az account show\n\n"
                result += "# Key Vault 목록 확인\n"
                result += "az keyvault list -o table\n"
                result += "```\n"
                return [TextContent(type="text", text=result)]
            
            result = "📋 사용 가능한 Key Vaults:\n\n"
            for vault in vaults:
                result += f"- **{vault['name']}**\n"
                result += f"  - Location: {vault['location']}\n"
                result += f"  - Resource Group: {vault['resourceGroup']}\n"
                result += f"  - URI: https://{vault['name']}.vault.azure.net/\n\n"
            
            result += "\n어느 Key Vault를 선택하시겠어요?"
            return [TextContent(type="text", text=result)]
        
        elif name == "select_keyvault":
            vault_name = arguments["vault_name"]
            KEYVAULT_URI = f"https://{vault_name}.vault.azure.net/"
            
            try:
                kv_manager = KeyVaultManager(KEYVAULT_URI, auth_manager.get_credential())
                return [TextContent(type="text", text=f"✅ Key Vault '{vault_name}' 선택됨\n\n다음 작업을 진행할 수 있습니다:\n- Secret 조회/등록/삭제\n- 인증서 조회/등록/교체/삭제")]
            except Exception as e: 
                error_msg = str(e)
                result = f"❌ Key Vault '{vault_name}' 연결 실패\n\n"
                result += f"**오류:** {error_msg}\n\n"
                
                if "403" in error_msg or "Forbidden" in error_msg: 
                    result += "**해결 방법:** 권한 부여가 필요합니다.\n"
                    result += "```bash\n"
                    result += f"az role assignment create \\\n"
                    result += f"  --role 'Key Vault Secrets Officer' \\\n"
                    result += f"  --assignee $(az ad signed-in-user show --query id -o tsv) \\\n"
                    result += f"  --scope $(az keyvault show --name {vault_name} --query id -o tsv)\n"
                    result += "```\n"
                elif "NotFound" in error_msg: 
                    result += f"**해결 방법:** Key Vault '{vault_name}'이 존재하지 않을 수 있습니다.\n"
                    result += "```bash\n"
                    result += f"az keyvault list --query \"[?name=='{vault_name}']\"\n"
                    result += "```\n"
                
                return [TextContent(type="text", text=result)]
        
        # Key Vault가 선택되지 않았으면 오류
        if not kv_manager:
            return [TextContent(type="text", text="❌ 먼저 Key Vault를 선택해야 합니다.\n\n1. `list_keyvaults`로 사용 가능한 Key Vault 확인\n2. `select_keyvault`로 Key Vault 선택\n\n또는 Key Vault 이름을 알고 있다면 바로 알려주세요.")]
        
        # === Secret 관리 ===
        if name == "set_secret":
            result = kv_manager.set_secret(arguments["name"], arguments["value"])
            if result["success"]:
                return [TextContent(type="text", text=f"✅ Secret '{result['name']}' 저장 완료\n버전: {result['version']}")]
            else:
                return [TextContent(type="text", text=f"❌ 오류: {result['error']}")]
        
        elif name == "get_secret": 
            result = kv_manager.get_secret(arguments["name"])
            if result["success"]: 
                return [TextContent(type="text", text=f"🔐 Secret '{result['name']}'\n값: {result['value']}\n버전: {result['version']}\n수정일: {result['updated']}")]
            else:
                return [TextContent(type="text", text=f"❌ {result['error']}")]
        
        elif name == "list_secrets":
            secrets = kv_manager.list_secrets()
            if not secrets:
                return [TextContent(type="text", text="📋 등록된 Secret이 없습니다.")]
            
            result = f"📋 총 {len(secrets)}개의 Secrets:\n\n"
            for secret in secrets:
                result += f"- **{secret['name']}**\n"
                result += f"  - Enabled: {secret['enabled']}\n"
                result += f"  - Updated: {secret['updated']}\n\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "delete_secret": 
            result = kv_manager.delete_secret(arguments["name"])
            if result["success"]: 
                return [TextContent(type="text", text=f"🗑️ Secret '{result['name']}' 삭제됨")]
            else:
                return [TextContent(type="text", text=f"❌ {result['error']}")]
        
        # === Certificate 관리 ===
        elif name == "import_certificate_from_pfx":
            pfx_bytes = base64.b64decode(arguments["pfx_base64"])
            password = arguments.get("password")
            
            result = kv_manager.import_certificate(
                arguments["name"],
                pfx_bytes,
                password
            )
            
            if result["success"]:
                return [TextContent(type="text", text=f"✅ 인증서 '{result['name']}' import 완료\nThumbprint: {result['thumbprint']}")]
            else:
                return [TextContent(type="text", text=f"❌ {result['error']}")]
        
        elif name == "convert_pem_to_pfx_and_import":
            import tempfile
            
            cert_pem = base64.b64decode(arguments["cert_pem_base64"])
            key_pem = base64.b64decode(arguments["key_pem_base64"])
            password = arguments.get("password")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as cert_file:
                cert_file.write(cert_pem)
                cert_path = cert_file.name
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as key_file:
                key_file.write(key_pem)
                key_path = key_file.name
            
            try:
                pfx_bytes = CertificateUtils.convert_pem_to_pfx(
                    cert_path,
                    key_path,
                    password
                )
                
                result = kv_manager.import_certificate(
                    arguments["name"],
                    pfx_bytes,
                    password
                )
                
                if result["success"]: 
                    return [TextContent(type="text", text=f"✅ PEM → PFX 변환 및 import 완료\n인증서:  '{result['name']}'\nThumbprint: {result['thumbprint']}")]
                else: 
                    return [TextContent(type="text", text=f"❌ {result['error']}")]
            
            finally:
                os.unlink(cert_path)
                os.unlink(key_path)
        
        elif name == "generate_self_signed_cert":
            pfx_bytes, thumbprint = CertificateUtils.generate_self_signed_cert(
                common_name=arguments["common_name"],
                password=arguments.get("password")
            )
            
            result = kv_manager.import_certificate(
                arguments["name"],
                pfx_bytes,
                arguments.get("password")
            )
            
            if result["success"]:
                return [TextContent(type="text", text=f"✅ 자체 서명 인증서 생성 및 import 완료\n인증서: '{result['name']}'\nCN: {arguments['common_name']}\nThumbprint: {thumbprint}")]
            else:
                return [TextContent(type="text", text=f"❌ {result['error']}")]
        
        elif name == "get_certificate": 
            result = kv_manager.get_certificate(arguments["name"])
            if result["success"]:
                return [TextContent(type="text", text=f"🔒 인증서 '{result['name']}'\nEnabled: {result['enabled']}\nCreated: {result['created']}\nExpires: {result['expires']}\nThumbprint: {result['thumbprint']}")]
            else:
                return [TextContent(type="text", text=f"❌ {result['error']}")]
        
        elif name == "list_certificates":
            certs = kv_manager.list_certificates()
            if not certs:
                return [TextContent(type="text", text="📋 등록된 인증서가 없습니다. ")]
            
            result = f"📋 총 {len(certs)}개의 인증서:\n\n"
            for cert in certs: 
                result += f"- **{cert['name']}**\n"
                result += f"  - Enabled: {cert['enabled']}\n"
                result += f"  - Expires: {cert['expires']}\n"
                result += f"  - Thumbprint: {cert['thumbprint']}\n\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "delete_certificate":
            result = kv_manager.delete_certificate(arguments["name"])
            if result["success"]:
                return [TextContent(type="text", text=f"🗑️ 인증서 '{result['name']}' 삭제됨")]
            else:
                return [TextContent(type="text", text=f"❌ {result['error']}")]
        
        elif name == "import_crt_certificate":
            cert_crt_bytes = base64.b64decode(arguments["cert_crt_base64"])
            key_bytes = base64.b64decode(arguments["key_base64"])
            password = arguments.get("password")
            
            try:
                pfx_bytes = CertificateUtils.convert_crt_bytes_to_pfx(
                    cert_crt_bytes,
                    key_bytes,
                    password
                )
                
                result = kv_manager.import_certificate(
                    arguments["name"],
                    pfx_bytes,
                    password
                )
                
                if result["success"]:
                    return [TextContent(type="text", text=f"✅ CRT → PFX 변환 및 import 완료\n인증서: '{result['name']}'\nThumbprint: {result['thumbprint']}")]
                else:
                    return [TextContent(type="text", text=f"❌ {result['error']}")]
            
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 변환 실패: {str(e)}")]
        
        elif name == "import_bundle_certificate":
            bundle_pem_bytes = base64.b64decode(arguments["bundle_pem_base64"])
            password = arguments.get("password")
            
            try:
                pfx_bytes = CertificateUtils.convert_bundle_pem_bytes_to_pfx(
                    bundle_pem_bytes,
                    password
                )
                
                result = kv_manager.import_certificate(
                    arguments["name"],
                    pfx_bytes,
                    password
                )
                
                if result["success"]:
                    return [TextContent(type="text", text=f"✅ 번들 PEM → PFX 변환 및 import 완료\n인증서: '{result['name']}'\nThumbprint: {result['thumbprint']}")]
                else:
                    return [TextContent(type="text", text=f"❌ {result['error']}")]
            
            except Exception as e: 
                return [TextContent(type="text", text=f"❌ 변환 실패: {str(e)}")]
        
        

        elif name == "import_certificate_with_chain":
            import tempfile
            
            cert_bytes = base64.b64decode(arguments["cert_base64"])
            key_bytes = base64.b64decode(arguments["key_base64"])
            chain_list = arguments.get("chain_base64_list", [])
            password = arguments.get("password")
            
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as cert_file:
                    cert_file.write(cert_bytes)
                    cert_path = cert_file.name
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as key_file:
                    key_file.write(key_bytes)
                    key_path = key_file.name
                
                chain_paths = []
                for i, chain_b64 in enumerate(chain_list):
                    chain_bytes = base64.b64decode(chain_b64)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_chain{i}.pem") as chain_file:
                        chain_file.write(chain_bytes)
                        chain_paths.append(chain_file.name)
                
                try:
                    pfx_bytes = CertificateUtils.convert_with_chain_to_pfx(
                        cert_path,
                        key_path,
                        chain_paths,
                        password
                    )
                    
                    result = kv_manager.import_certificate(
                        arguments["name"],
                        pfx_bytes,
                        password
                    )
                    
                    if result["success"]:
                        chain_info = f"({len(chain_list)}개 중간 인증서 포함)" if chain_list else ""
                        return [TextContent(type="text", text=f"✅ 인증서 체인 → PFX 변환 및 import 완료 {chain_info}\n인증서: '{result['name']}'\nThumbprint: {result['thumbprint']}")]
                    else:
                        return [TextContent(type="text", text=f"❌ {result['error']}")]
                
                finally:
                    os.unlink(cert_path)
                    os.unlink(key_path)
                    for chain_path in chain_paths:
                        os.unlink(chain_path)
            
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 변환 실패: {str(e)}")]
        
        elif name == "detect_certificate_format":
            cert_bytes = base64.b64decode(arguments["cert_base64"])
            
            try:
                cert_format = CertificateUtils.detect_format(cert_bytes)
                
                if cert_format == "PEM":
                    return [TextContent(type="text", text="📄 형식: PEM (텍스트 기반)\n사용 도구: convert_pem_to_pfx_and_import 또는 import_bundle_certificate")]
                elif cert_format == "DER":
                    return [TextContent(type="text", text="📄 형식: DER (바이너리)\n일반적으로 .crt 또는 .cer 확장자\n사용 도구: import_crt_certificate")]
                else:
                    return [TextContent(type="text", text=f"❓ 알 수 없는 형식\n첫 바이트: {cert_bytes[:20].hex()}")]
            
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 형식 감지 실패:  {str(e)}")]
        # server.py - @server.call_tool()에 추가

        elif name == "import_certificate_from_files":
            import os
            
            cert_path = arguments["cert_path"]
            key_path = arguments.get("key_path")
            chain_paths = arguments.get("chain_paths", [])
            password = arguments.get("password")
            
            # 파일 존재 확인
            if not os.path.exists(cert_path):
                return [TextContent(type="text", text=f"❌ 인증서 파일을 찾을 수 없습니다: {cert_path}")]
            
            if key_path and not os.path.exists(key_path):
                return [TextContent(type="text", text=f"❌ 개인키 파일을 찾을 수 없습니다: {key_path}")]
            
            try:
                # 파일 확장자로 형식 판단
                cert_ext = os.path.splitext(cert_path)[1].lower()
                
                # PFX 파일인 경우
                if cert_ext in ['.pfx', '.p12']:
                    with open(cert_path, 'rb') as f:
                        pfx_bytes = f.read()
                    
                    result = kv_manager.import_certificate(
                        arguments["name"],
                        pfx_bytes,
                        password
                    )
                    
                    if result["success"]:
                        return [TextContent(type="text", text=f"✅ PFX 파일 import 완료\n파일: {os.path.basename(cert_path)}\nThumbprint: {result['thumbprint']}")]
                    else:
                        return [TextContent(type="text", text=f"❌ {result['error']}")]
                
                # PEM/CRT 파일인 경우
                else:
                    if not key_path: 
                        return [TextContent(type="text", text="❌ PEM/CRT 형식은 개인키 파일(key_path)이 필요합니다.")]
                    
                    # 체인이 있는 경우
                    if chain_paths:
                        # 체인 파일 존재 확인
                        for chain_path in chain_paths: 
                            if not os.path.exists(chain_path):
                                return [TextContent(type="text", text=f"❌ 체인 파일을 찾을 수 없습니다: {chain_path}")]
                        
                        # 체인 포함 변환
                        pfx_bytes = CertificateUtils.convert_with_chain_to_pfx(
                            cert_path,
                            key_path,
                            chain_paths,
                            password
                        )
                        
                        result = kv_manager.import_certificate(
                            arguments["name"],
                            pfx_bytes,
                            password
                        )
                        
                        if result["success"]:
                            return [TextContent(type="text", text=f"✅ 인증서 체인 import 완료 ({len(chain_paths)}개 중간 인증서 포함)\n파일: {os.path.basename(cert_path)}\nThumbprint: {result['thumbprint']}")]
                        else:
                            return [TextContent(type="text", text=f"❌ {result['error']}")]
                    
                    # 체인 없이
                    else:
                        pfx_bytes = CertificateUtils.convert_pem_to_pfx(
                            cert_path,
                            key_path,
                            password
                        )
                        
                        result = kv_manager.import_certificate(
                            arguments["name"],
                            pfx_bytes,
                            password
                        )
                        
                        if result["success"]:
                            return [TextContent(type="text", text=f"✅ 인증서 import 완료\n파일: {os.path.basename(cert_path)}\nThumbprint: {result['thumbprint']}")]
                        else:
                            return [TextContent(type="text", text=f"❌ {result['error']}")]
            
            except ValueError as e:
                error_msg = str(e)
                if "암호화된" in error_msg or "비밀번호" in error_msg:
                    return [TextContent(type="text", text=f"❌ {error_msg}\n\n💡 해결 방법: password 파라미터에 비밀번호를 제공해주세요.\n예: import_certificate_from_files(name='...', cert_path='...', key_path='...', password='your_password')")]
                return [TextContent(type="text", text=f"❌ 파일 처리 실패: {error_msg}")]
            except Exception as e:
                error_msg = str(e)
                # PFX 비밀번호 관련 오류 확인
                if "password" in error_msg.lower() or "비밀번호" in error_msg.lower():
                    return [TextContent(type="text", text=f"❌ {error_msg}\n\n💡 해결 방법: PFX 파일이 암호화되어 있습니다. password 파라미터에 비밀번호를 제공해주세요.")]
                return [TextContent(type="text", text=f"❌ 파일 처리 실패: {error_msg}")]

        elif name == "import_pfx_from_file":
            import os
            
            pfx_path = arguments["pfx_path"]
            password = arguments.get("password")
            
            if not os.path.exists(pfx_path):
                return [TextContent(type="text", text=f"❌ PFX 파일을 찾을 수 없습니다: {pfx_path}")]
            
            try:
                with open(pfx_path, 'rb') as f:
                    pfx_bytes = f.read()
                
                result = kv_manager.import_certificate(
                    arguments["name"],
                    pfx_bytes,
                    password
                )
                
                if result["success"]:
                    return [TextContent(type="text", text=f"✅ PFX import 완료\n파일:  {os.path.basename(pfx_path)}\nThumbprint: {result['thumbprint']}")]
                else:
                    return [TextContent(type="text", text=f"❌ {result['error']}")]
            
            except Exception as e: 
                error_msg = str(e)
                # PFX 비밀번호 관련 오류 확인
                if "password" in error_msg.lower() or "비밀번호" in error_msg.lower():
                    return [TextContent(type="text", text=f"❌ {error_msg}\n\n💡 해결 방법: PFX 파일이 암호화되어 있습니다. password 파라미터에 비밀번호를 제공해주세요.")]
                return [TextContent(type="text", text=f"❌ 파일 읽기 실패: {error_msg}")]
        
        elif name == "decode_and_import_certificate":
            import tempfile
            import re
            
            cert_content = arguments["cert_content"]
            key_content = arguments.get("key_content")
            chain_contents = arguments.get("chain_contents", [])
            password = arguments.get("password")
            
            try:
                # cert_content가 base64인지 텍스트인지 판단
                # PEM 형식은 보통 "-----BEGIN"로 시작
                if cert_content.strip().startswith("-----BEGIN"):
                    cert_text = cert_content
                else:
                    # base64로 디코딩 시도
                    try:
                        cert_bytes = base64.b64decode(cert_content)
                        cert_text = cert_bytes.decode('utf-8', errors='ignore')
                    except:
                        cert_text = cert_content
                
                # key_content 처리
                key_text = None
                if key_content:
                    if key_content.strip().startswith("-----BEGIN"):
                        key_text = key_content
                    else:
                        try:
                            key_bytes = base64.b64decode(key_content)
                            key_text = key_bytes.decode('utf-8', errors='ignore')
                        except:
                            key_text = key_content
                
                # 번들 PEM인지 확인 (cert와 key가 하나의 파일에 있는 경우)
                if key_text and "-----BEGIN" in cert_text and "-----BEGIN" in key_text:
                    # cert와 key가 분리되어 있는 경우
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".pem") as cert_file:
                        cert_file.write(cert_text)
                        cert_path = cert_file.name
                    
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".pem") as key_file:
                        key_file.write(key_text)
                        key_path = key_file.name
                    
                    try:
                        # 체인이 있는 경우
                        if chain_contents:
                            chain_paths = []
                            for i, chain_content in enumerate(chain_contents):
                                if chain_content.strip().startswith("-----BEGIN"):
                                    chain_text = chain_content
                                else:
                                    try:
                                        chain_bytes = base64.b64decode(chain_content)
                                        chain_text = chain_bytes.decode('utf-8', errors='ignore')
                                    except:
                                        chain_text = chain_content
                                
                                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f"_chain{i}.pem") as chain_file:
                                    chain_file.write(chain_text)
                                    chain_paths.append(chain_file.name)
                            
                            pfx_bytes = CertificateUtils.convert_with_chain_to_pfx(
                                cert_path,
                                key_path,
                                chain_paths,
                                password
                            )
                            
                            # 임시 파일 정리
                            for chain_path in chain_paths:
                                os.unlink(chain_path)
                        else:
                            pfx_bytes = CertificateUtils.convert_pem_to_pfx(
                                cert_path,
                                key_path,
                                password
                            )
                        
                        result = kv_manager.import_certificate(
                            arguments["name"],
                            pfx_bytes,
                            password
                        )
                        
                        if result["success"]:
                            chain_info = f"({len(chain_contents)}개 중간 인증서 포함)" if chain_contents else ""
                            return [TextContent(type="text", text=f"✅ 인증서 자동 감지 및 import 완료 {chain_info}\n인증서: '{result['name']}'\nThumbprint: {result['thumbprint']}")]
                        else:
                            return [TextContent(type="text", text=f"❌ {result['error']}")]
                    
                    finally:
                        os.unlink(cert_path)
                        if key_path:
                            os.unlink(key_path)
                
                else:
                    # 번들 PEM 또는 단일 파일인 경우
                    bundle_text = cert_text
                    if key_text:
                        bundle_text = cert_text + "\n" + key_text
                    
                    bundle_bytes = bundle_text.encode('utf-8')
                    
                    try:
                        pfx_bytes = CertificateUtils.convert_bundle_pem_bytes_to_pfx(
                            bundle_bytes,
                            password
                        )
                        
                        result = kv_manager.import_certificate(
                            arguments["name"],
                            pfx_bytes,
                            password
                        )
                        
                        if result["success"]:
                            return [TextContent(type="text", text=f"✅ 번들 인증서 자동 감지 및 import 완료\n인증서: '{result['name']}'\nThumbprint: {result['thumbprint']}")]
                        else:
                            return [TextContent(type="text", text=f"❌ {result['error']}")]
                    
                    except ValueError as e:
                        error_msg = str(e)
                        if "암호화된" in error_msg or "비밀번호" in error_msg:
                            return [TextContent(type="text", text=f"❌ {error_msg}\n\n💡 해결 방법: password 파라미터에 비밀번호를 제공해주세요.")]
                        return [TextContent(type="text", text=f"❌ 인증서 처리 실패: {error_msg}\n\n형식을 확인해주세요. PEM, CRT, 또는 PFX 형식을 지원합니다.")]
                    except Exception as e:
                        error_msg = str(e)
                        if "password" in error_msg.lower() or "비밀번호" in error_msg.lower():
                            return [TextContent(type="text", text=f"❌ {error_msg}\n\n💡 해결 방법: 암호화된 파일입니다. password 파라미터에 비밀번호를 제공해주세요.")]
                        return [TextContent(type="text", text=f"❌ 인증서 처리 실패: {error_msg}\n\n형식을 확인해주세요. PEM, CRT, 또는 PFX 형식을 지원합니다.")]
            
            except ValueError as e:
                error_msg = str(e)
                if "암호화된" in error_msg or "비밀번호" in error_msg:
                    return [TextContent(type="text", text=f"❌ {error_msg}\n\n💡 해결 방법: password 파라미터에 비밀번호를 제공해주세요.")]
                return [TextContent(type="text", text=f"❌ 인증서 디코딩 실패: {error_msg}")]
            except Exception as e:
                error_msg = str(e)
                if "password" in error_msg.lower() or "비밀번호" in error_msg.lower():
                    return [TextContent(type="text", text=f"❌ {error_msg}\n\n💡 해결 방법: 암호화된 파일입니다. password 파라미터에 비밀번호를 제공해주세요.")]
                return [TextContent(type="text", text=f"❌ 인증서 디코딩 실패: {error_msg}")]
        
        elif name == "import_certificate_with_auto_chain":
            import os
            import glob
            import re
            
            cert_path = arguments["cert_path"]
            key_path = arguments["key_path"]
            chain_directory = arguments.get("chain_directory")
            chain_patterns = arguments.get("chain_patterns", [])
            password = arguments.get("password")
            
            # 파일 존재 확인
            if not os.path.exists(cert_path):
                return [TextContent(type="text", text=f"❌ 인증서 파일을 찾을 수 없습니다: {cert_path}")]
            
            if not os.path.exists(key_path):
                return [TextContent(type="text", text=f"❌ 개인키 파일을 찾을 수 없습니다: {key_path}")]
            
            try:
                # 체인 인증서 자동 검색
                
                # 체인 디렉토리 결정 (지정하지 않으면 cert_path와 같은 디렉토리)
                if chain_directory:
                    search_dir = chain_directory
                    if not os.path.exists(search_dir):
                        return [TextContent(type="text", text=f"❌ 체인 디렉토리를 찾을 수 없습니다: {search_dir}")]
                else:
                    search_dir = os.path.dirname(os.path.abspath(cert_path))
                
                # 절대 경로로 변환 (한 번만)
                abs_cert = os.path.abspath(cert_path)
                abs_key = os.path.abspath(key_path)
                chain_paths_set = set()
                
                # 체인 패턴이 지정된 경우
                if chain_patterns:
                    for pattern in chain_patterns:
                        # glob 패턴 사용
                        full_pattern = os.path.join(search_dir, pattern)
                        matches = glob.glob(full_pattern)
                        for match in matches:
                            # cert_path나 key_path와 중복되지 않도록
                            abs_match = os.path.abspath(match)
                            if abs_match != abs_cert and abs_match != abs_key:
                                chain_paths_set.add(abs_match)
                
                # 패턴이 지정되지 않은 경우 자동 감지
                else:
                    # 일반적인 체인 인증서 파일 이름 패턴
                    auto_patterns = [
                        "chain*.crt", "chain*.pem", "chain*.cer",
                        "intermediate*.crt", "intermediate*.pem", "intermediate*.cer",
                        "ca*.crt", "ca*.pem", "ca*.cer",
                        "*chain*.crt", "*chain*.pem", "*chain*.cer",
                        "*intermediate*.crt", "*intermediate*.pem", "*intermediate*.cer"
                    ]
                    
                    cert_basename = os.path.splitext(os.path.basename(cert_path))[0]
                    key_basename = os.path.splitext(os.path.basename(key_path))[0]
                    
                    for pattern in auto_patterns:
                        full_pattern = os.path.join(search_dir, pattern)
                        matches = glob.glob(full_pattern)
                        for match in matches:
                            abs_match = os.path.abspath(match)
                            
                            # cert나 key 파일이 아니고, 이미 추가되지 않은 경우
                            if abs_match != abs_cert and abs_match != abs_key:
                                # 파일 이름이 cert나 key와 유사하지 않은 경우만 추가
                                match_basename = os.path.splitext(os.path.basename(match))[0].lower()
                                if (match_basename != cert_basename.lower() and 
                                    match_basename != key_basename.lower() and
                                    not match_basename.startswith(cert_basename.lower()) and
                                    not match_basename.startswith(key_basename.lower())):
                                    chain_paths_set.add(abs_match)
                    
                    # 추가로 디렉토리 내의 모든 .crt, .pem, .cer 파일을 확인
                    # (단, cert와 key는 제외)
                    for ext in ['.crt', '.pem', '.cer']:
                        pattern = os.path.join(search_dir, f"*{ext}")
                        matches = glob.glob(pattern)
                        for match in matches:
                            abs_match = os.path.abspath(match)
                            
                            if abs_match != abs_cert and abs_match != abs_key:
                                # 파일 내용을 확인하여 인증서인지 판단
                                try:
                                    with open(abs_match, 'rb') as f:
                                        content = f.read()
                                        # PEM 형식 확인
                                        if b'-----BEGIN CERTIFICATE-----' in content:
                                            chain_paths_set.add(abs_match)
                                        # DER 형식도 가능하지만, 일단 PEM만 확인
                                except Exception:
                                    pass
                
                # 중복 제거 및 정렬
                chain_paths = sorted(chain_paths_set)
                
                # 파일 확장자로 형식 판단
                cert_ext = os.path.splitext(cert_path)[1].lower()
                
                # PFX 파일인 경우는 그냥 import
                if cert_ext in ['.pfx', '.p12']:
                    with open(cert_path, 'rb') as f:
                        pfx_bytes = f.read()
                    
                    result = kv_manager.import_certificate(
                        arguments["name"],
                        pfx_bytes,
                        password
                    )
                    
                    if result["success"]:
                        return [TextContent(type="text", text=f"✅ PFX 파일 import 완료\n파일: {os.path.basename(cert_path)}\nThumbprint: {result['thumbprint']}")]
                    else:
                        return [TextContent(type="text", text=f"❌ {result['error']}")]
                
                # PEM/CRT 파일인 경우 변환 필요
                else:
                    # 체인 인증서가 발견된 경우
                    if chain_paths:
                        # 체인 파일 존재 확인
                        for chain_path in chain_paths:
                            if not os.path.exists(chain_path):
                                return [TextContent(type="text", text=f"❌ 체인 파일을 찾을 수 없습니다: {chain_path}")]
                        
                        # 체인 포함 변환
                        pfx_bytes = CertificateUtils.convert_with_chain_to_pfx(
                            cert_path,
                            key_path,
                            chain_paths,
                            password
                        )
                        
                        result = kv_manager.import_certificate(
                            arguments["name"],
                            pfx_bytes,
                            password
                        )
                        
                        if result["success"]:
                            chain_files = [os.path.basename(p) for p in chain_paths]
                            return [TextContent(type="text", text=f"✅ 인증서 + 체인 자동 감지 및 import 완료\n\n**주 인증서:** {os.path.basename(cert_path)}\n**개인키:** {os.path.basename(key_path)}\n**체인 인증서 ({len(chain_paths)}개):**\n" + "\n".join([f"  - {f}" for f in chain_files]) + f"\n\n**Thumbprint:** {result['thumbprint']}")]
                        else:
                            return [TextContent(type="text", text=f"❌ {result['error']}")]
                    
                    # 체인 인증서가 없는 경우
                    else:
                        pfx_bytes = CertificateUtils.convert_pem_to_pfx(
                            cert_path,
                            key_path,
                            password
                        )
                        
                        result = kv_manager.import_certificate(
                            arguments["name"],
                            pfx_bytes,
                            password
                        )
                        
                        if result["success"]:
                            return [TextContent(type="text", text=f"✅ 인증서 import 완료 (체인 인증서 없음)\n**주 인증서:** {os.path.basename(cert_path)}\n**개인키:** {os.path.basename(key_path)}\n**Thumbprint:** {result['thumbprint']}\n\n💡 체인 인증서가 있다면 같은 디렉토리에 두고 다시 시도하세요.")]
                        else:
                            return [TextContent(type="text", text=f"❌ {result['error']}")]
            
            except ValueError as e:
                error_msg = str(e)
                if "암호화된" in error_msg or "비밀번호" in error_msg:
                    return [TextContent(type="text", text=f"❌ {error_msg}\n\n💡 해결 방법: password 파라미터에 비밀번호를 제공해주세요.")]
                import traceback
                error_detail = traceback.format_exc()
                return [TextContent(type="text", text=f"❌ 파일 처리 실패: {error_msg}\n\n상세:\n{error_detail}")]
            except Exception as e:
                error_msg = str(e)
                if "password" in error_msg.lower() or "비밀번호" in error_msg.lower():
                    return [TextContent(type="text", text=f"❌ {error_msg}\n\n💡 해결 방법: 암호화된 파일입니다. password 파라미터에 비밀번호를 제공해주세요.")]
                import traceback
                error_detail = traceback.format_exc()
                return [TextContent(type="text", text=f"❌ 파일 처리 실패: {error_msg}\n\n상세:\n{error_detail}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"❌ 예외 발생: {str(e)}")]

async def main():
    print("🚀 Azure Key Vault MCP Server 시작", file=sys.stderr)
    
    # 현재 구독 정보 표시
    sub = auth_manager.get_current_subscription()
    if sub:
        print(f"📋 구독: {sub['name']} ({sub['id']})", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="azure-keyvault",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())

# server.py - @server.list_tools() 다음에 추가

@server.list_prompts()
async def handle_list_prompts():
    """Agent 사용 가이드"""
    return [
        {
            "name": "agent_intro",
            "description": "Azure Key Vault 관리 Agent 소개",
            "arguments": []
        }
    ]

@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict):
    if name == "agent_intro": 
        return {
            "messages": [
                {
                    "role": "system",
                    "content": """# Azure Key Vault 관리 전문 Agent

당신은 **Azure Key Vault Secret 및 Certificate 관리 전문가**입니다.

## 🎯 전문 분야

### Secret 관리
- Secret 등록/업데이트 (set_secret)
- Secret 조회 (get_secret)
- Secret 목록 (list_secrets)
- Secret 삭제 (delete_secret)

### Certificate 관리
- 인증서 등록 (PFX, PEM, CRT, 번들 지원)
- 인증서 형식 자동 변환
- 인증서 조회 (get_certificate)
- 인증서 목록 (list_certificates)
- 인증서 삭제 (delete_certificate)

### 인증 관리
- Azure 인증 자동 체크 (check_azure_auth)
- Key Vault 목록 조회 (list_keyvaults)
- Key Vault 선택 (select_keyvault)

## 🚫 전문 분야가 아닌 것

App Service, VM, 네트워크, Storage 등 다른 Azure 리소스는 다루지 않습니다. 

## 📝 대화 원칙

1. **도구 우선 사용**: 설명보다 MCP 도구를 먼저 실행
2. **단계적 진행**: 한 번에 하나씩
3. **간결한 응답**: 결과만 명확히
4. **자동 흐름**: 인증 체크 → Key Vault 선택 → 작업 수행

## 🔄 표준 워크플로우

사용자가 인증서/Secret 작업 요청 시: 

1. check_azure_auth (자동)
2. list_keyvaults (필요 시)
3. select_keyvault (사용자 선택)
4. 작업 실행
5. 결과 간결히 보고

## 💬 좋은 대화 예시

User: 인증서 교체 필요해
AI: [check_azure_auth] ✅
    [list_keyvaults] 📋 1. kv-prod 2.kv-test
    어느 Vault인가요? 
User: kv-prod
AI: [select_keyvault] ✅
    [list_certificates] 📋 1.ssl-cert
    어떤 인증서를 교체하시겠어요? 

## ⚡ 즉시 실행

구체적 요청은 바로 도구 실행: 
- "kv-prod의 secret 목록" → 즉시 select + list 실행
- "db-password 조회" → 즉시 get_secret 실행"""
                }
            ]
        }

# server.py - @server.list_prompts() 다음에 추가

@server.list_resources()
async def handle_list_resources():
    """Agent가 관리하는 리소스 정의"""
    resources = [
        {
            "uri": "azure://keyvault/info",
            "name": "Agent Information",
            "description": "Azure Key Vault 관리 Agent 정보",
            "mimeType": "text/plain"
        }
    ]
    
    # Key Vault가 선택되어 있으면 리소스 추가
    if kv_manager: 
        resources.extend([
            {
                "uri": "azure://keyvault/secrets",
                "name": "Key Vault Secrets",
                "description": f"현재 Key Vault의 모든 Secret 목록",
                "mimeType": "application/json"
            },
            {
                "uri": "azure://keyvault/certificates",
                "name": "Key Vault Certificates",
                "description": f"현재 Key Vault의 모든 인증서 목록",
                "mimeType": "application/json"
            }
        ])
    
    return resources

@server.read_resource()
async def handle_read_resource(uri: str):
    """리소스 내용 반환"""
    if uri == "azure://keyvault/info":
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": """Azure Key Vault 관리 전문 Agent

전문 분야: 
- Secret 관리 (등록/조회/목록/삭제)
- Certificate 관리 (등록/조회/목록/삭제/변환)
- Azure 인증 및 Key Vault 선택

비전문 분야:
- App Service, VM, 네트워크, Storage 등 다른 Azure 리소스

사용 방법:
1. "인증 상태 확인해줘"
2. "Key Vault 목록 보여줘"
3. "kv-prod 선택해줘"
4. "secret 목록 조회해줘"
5. "인증서 교체해줘" """
                }
            ]
        }
    
    elif uri == "azure://keyvault/secrets" and kv_manager:
        secrets = kv_manager.list_secrets()
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(secrets, indent=2, ensure_ascii=False)
                }
            ]
        }
    
    elif uri == "azure://keyvault/certificates" and kv_manager:
        certs = kv_manager.list_certificates()
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(certs, indent=2, ensure_ascii=False)
                }
            ]
        }
    
    else:
        raise ValueError(f"Unknown resource: {uri}")
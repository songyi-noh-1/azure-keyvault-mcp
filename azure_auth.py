# azure_auth.py
import subprocess
import sys
import json
from typing import Optional, List, Dict, Tuple

class AzureAuthManager: 
    """Azure 인증 및 구독 관리"""
    
    def __init__(self, auto_login: bool = False):
        """
        Args:
            auto_login: True면 로그인 안 되어 있을 때 자동 로그인 시도
                       False면 로그인 상태만 체크 (MCP 서버용)
        """
        self.credential = None
        self.is_authenticated = False
        self.auth_message = ""
        
        if auto_login:
            self._ensure_authenticated()
        else:
            self._check_authentication_status()
    
    def _check_authentication_status(self) -> Tuple[bool, str]:
        """인증 상태 체크 (로그인 시도 안 함)"""
        
        # Azure CLI 설치 확인
        if not self._check_azure_cli_installed():
            self.is_authenticated = False
            self.auth_message = "Azure CLI가 설치되지 않았습니다.\n설치:  https://learn.microsoft.com/cli/azure/install-azure-cli"
            return False, self.auth_message
        
        # 로그인 상태 확인
        if not self._check_logged_in():
            self.is_authenticated = False
            self.auth_message = "Azure에 로그인되어 있지 않습니다.\n실행:  az login"
            return False, self.auth_message
        
        # Credential 초기화
        try:
            from azure.identity import DefaultAzureCredential
            self.credential = DefaultAzureCredential()
            self.is_authenticated = True
            self.auth_message = "Azure 인증 성공"
            return True, self.auth_message
        except Exception as e:
            self.is_authenticated = False
            self.auth_message = f"인증 초기화 실패: {str(e)}"
            return False, self.auth_message
    
    def _ensure_authenticated(self):
        """Azure 인증 확인 및 로그인 유도 (대화형)"""
        print("🔐 Azure 인증 확인 중.. .", file=sys.stderr)
        
        # Azure CLI 설치 확인
        if not self._check_azure_cli_installed():
            print("❌ Azure CLI가 설치되지 않았습니다.", file=sys.stderr)
            print("설치: https://learn.microsoft.com/cli/azure/install-azure-cli", file=sys. stderr)
            sys.exit(1)
        
        # 로그인 상태 확인
        if not self._check_logged_in():
            print("❌ Azure에 로그인되어 있지 않습니다.", file=sys.stderr)
            print("", file=sys.stderr)
            response = input("지금 로그인하시겠습니까? (y/n): ")
            
            if response.lower() == 'y':
                self._perform_login()
            else:
                print("로그인이 필요합니다.  'az login'을 실행하세요.", file=sys.stderr)
                sys.exit(1)
        
        # Credential 초기화
        try: 
            from azure.identity import DefaultAzureCredential
            self.credential = DefaultAzureCredential()
            self.is_authenticated = True
            print("✅ Azure 인증 성공", file=sys. stderr)
        except Exception as e:
            print(f"❌ 인증 초기화 실패: {e}", file=sys.stderr)
            sys.exit(1)
    
    def _check_azure_cli_installed(self) -> bool:
        """Azure CLI 설치 확인"""
        try:
            import platform
            is_windows = platform.system() == "Windows"
            
            # Windows에서는 az.cmd를 사용하거나 shell=True로 실행
            if is_windows:
                # Windows에서는 shell=True를 사용하여 PATH에서 az.cmd를 찾도록 함
                result = subprocess.run(
                    "az --version",
                    capture_output=True,
                    timeout=5,
                    shell=True
                )
            else:
                result = subprocess.run(
                    ["az", "--version"],
                    capture_output=True,
                    timeout=5,
                    shell=False
                )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _check_logged_in(self) -> bool:
        """Azure CLI 로그인 상태 확인"""
        try:
            import platform
            is_windows = platform.system() == "Windows"
            
            # Windows에서는 shell=True로 문자열 명령 사용
            if is_windows:
                result = subprocess.run(
                    "az account show",
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
            else:
                result = subprocess.run(
                    ["az", "account", "show"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=False
                )
            
            # 디버깅을 위해 에러 출력 (stderr로)
            if result.returncode != 0:
                print(f"⚠️ az account show 실패: {result.stderr}", file=sys.stderr)
            
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("⚠️ az account show 타임아웃", file=sys.stderr)
            return False
        except Exception as e:
            print(f"⚠️ az account show 오류: {str(e)}", file=sys.stderr)
            return False
    
    def _perform_login(self):
        """Azure CLI 로그인 실행"""
        print("🔐 브라우저에서 로그인을 진행하세요...", file=sys.stderr)
        try:
            import platform
            is_windows = platform.system() == "Windows"
            
            if is_windows:
                result = subprocess.run(
                    "az login",
                    timeout=120,
                    shell=True
                )
            else:
                result = subprocess.run(
                    ["az", "login"],
                    timeout=120,
                    shell=False
                )
            
            if result.returncode == 0:
                print("✅ 로그인 성공!", file=sys.stderr)
                # Credential 재초기화
                from azure.identity import DefaultAzureCredential
                self.credential = DefaultAzureCredential()
                self.is_authenticated = True
            else:
                print("❌ 로그인 실패", file=sys.stderr)
                sys.exit(1)
        except subprocess.TimeoutExpired:
            print("❌ 로그인 타임아웃", file=sys.stderr)
            sys.exit(1)
    
    def get_credential(self):
        """Credential 반환"""
        return self.credential
    
    def get_auth_status(self) -> Dict:
        """인증 상태 정보 반환"""
        return {
            "authenticated": self.is_authenticated,
            "message": self.auth_message,
            "subscription": self.get_current_subscription() if self.is_authenticated else None
        }
    
    def list_keyvaults(self) -> List[Dict[str, str]]:
        """현재 구독의 모든 Key Vault 목록 조회"""
        if not self.is_authenticated:
            return []
        
        print("📋 Key Vault 목록 조회 중...", file=sys. stderr)
        
        try:
            import platform
            is_windows = platform.system() == "Windows"
            
            cmd = "az keyvault list --query \"[].{name:name, location:location, resourceGroup:resourceGroup}\" -o json"
            
            if is_windows:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=True
                )
            else:
                result = subprocess.run(
                    ["az", "keyvault", "list", "--query", "[].{name:name, location:location, resourceGroup:resourceGroup}", "-o", "json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=False
                )
            
            if result.returncode == 0:
                vaults = json.loads(result. stdout)
                print(f"✅ {len(vaults)}개의 Key Vault 발견", file=sys.stderr)
                return vaults
            else:
                print(f"❌ Key Vault 목록 조회 실패: {result.stderr}", file=sys.stderr)
                return []
        
        except Exception as e:
            print(f"❌ 오류:  {e}", file=sys.stderr)
            return []
    
    def get_current_subscription(self) -> Optional[Dict]:
        """현재 구독 정보 조회"""
        try:
            import platform
            is_windows = platform.system() == "Windows"
            
            if is_windows:
                result = subprocess.run(
                    "az account show -o json",
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
            else:
                result = subprocess.run(
                    ["az", "account", "show", "-o", "json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=False
                )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            return None
        
        except Exception: 
            return None

    def refresh_auth_status(self) -> bool:
        """인증 상태 재확인 (로그인 후 호출)"""
        print("🔄 인증 상태 재확인 중.. .", file=sys.stderr)
        
        # 로그인 상태 다시 체크
        if not self._check_logged_in():
            self.is_authenticated = False
            self.auth_message = "Azure에 로그인되어 있지 않습니다.\n실행:  az login"
            return False
        
        # Credential 재초기화
        try:
            from azure.identity import DefaultAzureCredential
            self.credential = DefaultAzureCredential()
            self.is_authenticated = True
            self.auth_message = "Azure 인증 성공"
            print("✅ 인증 상태 업데이트 완료", file=sys.stderr)
            return True
        except Exception as e: 
            self.is_authenticated = False
            self.auth_message = f"인증 초기화 실패: {str(e)}"
            return False
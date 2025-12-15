import subprocess
import sys
import json
import os
from typing import Optional, List, Dict, Tuple

# Windows에서 한글 출력을 위한 인코딩 설정
if sys.platform == 'win32':
    # 환경 변수를 먼저 설정 (가장 중요!)
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '0'  # Windows 10+ UTF-8 모드 활성화
    
    # Windows 코드 페이지를 UTF-8로 설정 (Python 3.7+)
    try:
        import locale
        # UTF-8 locale 설정 시도
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except (locale.Error, OSError):
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except (locale.Error, OSError):
            pass  # 실패해도 계속 진행
    
    # stdout/stderr 인코딩 설정
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    
    # Windows 콘솔 코드 페이지를 UTF-8로 설정 (가능한 경우)
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # CP_UTF8 = 65001
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
    except (OSError, AttributeError):
        pass  # 실패해도 계속 진행

class AzureAuthManager: 
    """Azure 인증 및 구독 관리"""
    
    def __init__(self, auto_login: bool = False, lazy_init: bool = True):
        """
        Args:
            auto_login: True면 로그인 안 되어 있을 때 자동 로그인 시도
                       False면 로그인 상태만 체크 (MCP 서버용)
            lazy_init: True면 초기화 시 인증 체크를 건너뛰고, 필요할 때만 체크 (빠른 시작)
        """
        self.credential = None
        self.is_authenticated = False
        self.auth_message = ""
        self._initialized = False
        
        if auto_login:
            self._ensure_authenticated()
            self._initialized = True
        elif not lazy_init:
            self._check_authentication_status()
            self._initialized = True
        # lazy_init=True이면 초기화 건너뛰기 (서버 시작 빠르게)
    
    def _ensure_initialized(self):
        """필요할 때만 인증 상태 체크 (지연 초기화)"""
        if not self._initialized:
            self._check_authentication_status()
            self._initialized = True
    
    def _check_authentication_status(self) -> Tuple[bool, str]:
        """인증 상태 체크 (AzureCliCredential 직접 사용, 매우 빠름)"""
        
        # Azure CLI가 이미 로그인되어 있으므로 AzureCliCredential을 직접 사용 (가장 빠름)
        try:
            from azure.identity import AzureCliCredential
            from azure.core.exceptions import ClientAuthenticationError
            
            # AzureCliCredential 직접 사용 (다른 인증 방법 시도 없이 바로 Azure CLI 사용)
            credential = AzureCliCredential()
            
            # 토큰 가져오기로 인증 확인
            try:
                # get_token을 호출하여 실제로 인증이 되는지 확인
                token = credential.get_token("https://management.azure.com/.default")
                
                if token and token.token:
                    # 성공 시 DefaultAzureCredential로 전환 (다른 작업에서도 사용 가능하도록)
                    from azure.identity import DefaultAzureCredential
                    self.credential = DefaultAzureCredential(
                        exclude_managed_identity_credential=True,
                    )
                    self.is_authenticated = True
                    self.auth_message = "Azure 인증 성공"
                    return True, self.auth_message
                else:
                    self.is_authenticated = False
                    self.auth_message = "Azure에 로그인되어 있지 않습니다.\n실행:  az login"
                    return False, self.auth_message
                    
            except ClientAuthenticationError as e:
                # 인증 실패
                self.is_authenticated = False
                error_msg = str(e)
                if "az login" in error_msg.lower() or "not logged in" in error_msg.lower() or "Please run 'az login'" in error_msg:
                    self.auth_message = "Azure에 로그인되어 있지 않습니다.\n실행:  az login"
                else:
                    self.auth_message = f"인증 실패: {error_msg}"
                return False, self.auth_message
            except Exception as e:
                # 다른 오류 (예: Azure CLI가 설치되지 않음)
                error_msg = str(e).lower()
                if "az" in error_msg or "cli" in error_msg:
                    self.is_authenticated = False
                    self.auth_message = "Azure CLI가 설치되지 않았거나 로그인되어 있지 않습니다.\n실행:  az login"
                else:
                    self.is_authenticated = False
                    self.auth_message = f"인증 확인 중 오류: {str(e)}"
                return False, self.auth_message
            
        except ImportError:
            # Azure SDK가 없는 경우
            self.is_authenticated = False
            self.auth_message = "Azure Python SDK가 설치되지 않았습니다.\n설치:  pip install azure-identity"
            return False, self.auth_message
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
        """Azure CLI 설치 확인 (빠른 체크)"""
        try:
            import platform
            is_windows = platform.system() == "Windows"
            
            # 빠른 체크: where/which로 먼저 확인 (az --version보다 훨씬 빠름)
            if is_windows:
                quick_check = subprocess.run(
                    "where az",
                    capture_output=True,
                    timeout=2,
                    shell=True,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                quick_check = subprocess.run(
                    ["which", "az"],
                    capture_output=True,
                    timeout=2,
                    shell=False,
                    encoding='utf-8',
                    errors='replace'
                )
            
            # where/which가 성공하면 Azure CLI가 설치되어 있다고 간주
            if quick_check.returncode == 0:
                return True
            
            # where/which가 실패하면 az --version으로 재확인 (느리지만 확실함)
            timeout = 5  # 타임아웃을 5초로 단축
            if is_windows:
                result = subprocess.run(
                    "az --version",
                    capture_output=True,
                    timeout=timeout,
                    shell=True,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                result = subprocess.run(
                    ["az", "--version"],
                    capture_output=True,
                    timeout=timeout,
                    shell=False,
                    encoding='utf-8',
                    errors='replace'
                )
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except subprocess.TimeoutExpired:
            # 타임아웃 발생 시 where/which 결과로 판단
            return False
        except Exception as e:
            print(f"⚠️ Azure CLI 체크 중 오류: {e}", file=sys.stderr)
            return False
    
    def _check_logged_in(self, timeout_override: Optional[int] = None) -> bool:
        """Azure CLI 로그인 상태 확인 (최적화된 버전)
        
        Args:
            timeout_override: 타임아웃 시간 오버라이드 (None이면 기본값 사용)
        """
        try:
            import platform
            is_windows = platform.system() == "Windows"
            
            # 타임아웃 설정
            if timeout_override is not None:
                timeout = timeout_override
            else:
                timeout = 5  # 기본값을 5초로 단축
            
            # 환경 변수 준비 (Azure CLI 초기화 시간 단축)
            env = os.environ.copy()
            # Azure CLI가 빠르게 시작하도록 환경 변수 설정
            env['AZURE_CORE_NO_COLOR'] = '1'  # 색상 출력 비활성화로 빠른 시작
            env['AZURE_LOGGING_LEVEL'] = 'ERROR'  # 로깅 최소화
            
            # Windows에서는 shell=True로 실행 (환경 변수와 PATH 자동 상속)
            if is_windows:
                # shell=True로 실행하면 현재 PowerShell 세션의 환경 변수와 PATH가 상속됨
                result = subprocess.run(
                    "az account show",
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=True,  # shell=True로 변경
                    encoding='utf-8',
                    errors='replace',
                    env=env
                )
            else:
                result = subprocess.run(
                    ["az", "account", "show"],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=False,
                    encoding='utf-8',
                    errors='replace',
                    env=env
                )
            
            # 디버깅을 위해 에러 출력 (stderr로)
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "알 수 없는 오류"
                # 타임아웃이 아닌 경우에만 에러 출력 (타임아웃은 별도 처리)
                if "timeout" not in error_msg.lower():
                    print(f"⚠️ az account show 실패: {error_msg}", file=sys.stderr)
            
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"⚠️ az account show 타임아웃 ({timeout}초 초과). Azure CLI가 느리게 응답하고 있습니다.", file=sys.stderr)
            print("💡 해결 방법: PowerShell에서 'az account show'를 직접 실행해보고 응답 시간을 확인하세요.", file=sys.stderr)
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
                    shell=True,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                result = subprocess.run(
                    ["az", "login"],
                    timeout=120,
                    shell=False,
                    encoding='utf-8',
                    errors='replace'
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
        self._ensure_initialized()
        return self.credential
    
    def get_auth_status(self, include_subscription: bool = True) -> Dict:
        """인증 상태 정보 반환
        
        Args:
            include_subscription: True면 구독 정보도 조회 (느릴 수 있음), False면 구독 정보 없이 반환
        """
        self._ensure_initialized()
        
        subscription = None
        if include_subscription and self.is_authenticated:
            try:
                subscription = self.get_current_subscription()
            except Exception:
                # 구독 정보 조회 실패해도 인증 상태는 반환
                pass
        
        return {
            "authenticated": self.is_authenticated,
            "message": self.auth_message,
            "subscription": subscription
        }
    
    def list_keyvaults(self) -> List[Dict[str, str]]:
        """현재 선택된 구독의 모든 Key Vault 목록 조회 (Azure Python SDK 사용)"""
        # 지연 초기화: 필요할 때만 인증 체크
        self._ensure_initialized()
        
        if not self.is_authenticated or not self.credential:
            return []
        
        print("📋 Key Vault 목록 조회 중...", file=sys.stderr)
        
        try:
            # Azure Python SDK를 직접 사용 (subprocess보다 훨씬 빠름)
            from azure.mgmt.keyvault import KeyVaultManagementClient
            from azure.mgmt.resource import ResourceManagementClient
            
            # 현재 선택된 구독 정보 가져오기
            subscription_id = self._get_subscription_id()
            if not subscription_id:
                print("❌ 구독 ID를 가져올 수 없습니다.", file=sys.stderr)
                return []
            
            # 구독 정보 확인 및 표시
            try:
                subscription = self.get_current_subscription()
                if subscription:
                    sub_name = subscription.get('displayName') or subscription.get('name', 'N/A')
                    print(f"📌 현재 구독: {sub_name} ({subscription_id[:8]}...)", file=sys.stderr)
            except Exception:
                print(f"📌 현재 구독 ID: {subscription_id[:8]}...", file=sys.stderr)
            
            # Key Vault Management Client 생성
            kv_client = KeyVaultManagementClient(self.credential, subscription_id)
            
            # Resource Management Client 생성 (리소스 그룹 정보용)
            resource_client = ResourceManagementClient(self.credential, subscription_id)
            
            vaults = []
            
            # 모든 Key Vault 조회 (현재 구독의 것만)
            vault_list = kv_client.vaults.list()
            
            for vault in vault_list:
                # 리소스 그룹 이름 추출 (ID에서)
                resource_group = vault.id.split('/resourceGroups/')[1].split('/')[0] if '/resourceGroups/' in vault.id else None
                
                vaults.append({
                    "name": vault.name,
                    "location": vault.location,
                    "resourceGroup": resource_group
                })
            
            print(f"✅ {len(vaults)}개의 Key Vault 발견", file=sys.stderr)
            return vaults
        
        except ImportError as e:
            # SDK가 없는 경우 fallback to Azure CLI
            print("⚠️ Azure Management SDK를 사용할 수 없습니다. Azure CLI로 대체합니다...", file=sys.stderr)
            return self._list_keyvaults_via_cli()
        except Exception as e:
            print(f"⚠️ SDK 조회 실패, Azure CLI로 대체합니다: {e}", file=sys.stderr)
            return self._list_keyvaults_via_cli()
    
    def _list_keyvaults_via_cli(self) -> List[Dict[str, str]]:
        """Azure CLI를 통한 Key Vault 목록 조회 (fallback, 최적화된 버전)"""
        print("📋 Key Vault 목록 조회 중 (Azure CLI)...", file=sys.stderr)
        
        try:
            import platform
            is_windows = platform.system() == "Windows"
            
            # 환경 변수 준비 (Azure CLI 초기화 시간 단축)
            env = os.environ.copy()
            env['AZURE_CORE_NO_COLOR'] = '1'
            env['AZURE_LOGGING_LEVEL'] = 'ERROR'
            
            timeout = 30  # Key Vault 목록은 시간이 좀 걸릴 수 있음
            
            if is_windows:
                # PowerShell을 통해 실행 (환경 변수 상속)
                # JSON 쿼리 문자열을 PowerShell에서 올바르게 처리하도록 이스케이프
                ps_command = 'az keyvault list --query "[].{name:name, location:location, resourceGroup:resourceGroup}" -o json'
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command', ps_command],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=False,
                    encoding='utf-8',
                    errors='replace',
                    env=env
                )
            else:
                result = subprocess.run(
                    ["az", "keyvault", "list", "--query", "[].{name:name, location:location, resourceGroup:resourceGroup}", "-o", "json"],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=False,
                    encoding='utf-8',
                    errors='replace',
                    env=env
                )
            
            if result.returncode == 0:
                vaults = json.loads(result.stdout)
                print(f"✅ {len(vaults)}개의 Key Vault 발견", file=sys.stderr)
                return vaults
            else:
                error_msg = result.stderr.strip() if result.stderr else "알 수 없는 오류"
                print(f"❌ Key Vault 목록 조회 실패: {error_msg}", file=sys.stderr)
                return []
        
        except subprocess.TimeoutExpired:
            print(f"❌ Key Vault 목록 조회 타임아웃 ({timeout}초 초과)", file=sys.stderr)
            return []
        except Exception as e:
            print(f"❌ 오류: {e}", file=sys.stderr)
            return []
    
    def _get_subscription_id(self) -> Optional[str]:
        """현재 선택된 구독 ID 가져오기 (Azure CLI 설정 파일에서 확인)"""
        try:
            # 먼저 Azure CLI 설정 파일에서 현재 선택된 구독 확인
            # Windows: %USERPROFILE%\.azure\azureProfile.json
            # Linux/Mac: ~/.azure/azureProfile.json
            import platform
            is_windows = platform.system() == "Windows"
            
            if is_windows:
                azure_profile_path = os.path.join(os.environ.get('USERPROFILE', ''), '.azure', 'azureProfile.json')
            else:
                azure_profile_path = os.path.join(os.path.expanduser('~'), '.azure', 'azureProfile.json')
            
            # Azure CLI 설정 파일 읽기
            if os.path.exists(azure_profile_path):
                try:
                    # UTF-8 BOM 처리 (utf-8-sig 사용)
                    with open(azure_profile_path, 'r', encoding='utf-8-sig') as f:
                        azure_profile = json.load(f)
                    
                    # subscriptions 배열에서 isDefault가 true인 구독 찾기
                    subscriptions = azure_profile.get('subscriptions', [])
                    for sub in subscriptions:
                        if sub.get('isDefault', False):
                            subscription_id = sub.get('id')
                            if subscription_id:
                                # /subscriptions/ 접두사 제거
                                if subscription_id.startswith("/subscriptions/"):
                                    subscription_id = subscription_id.split("/subscriptions/")[1].split("/")[0]
                                return subscription_id
                except Exception as e:
                    print(f"⚠️ Azure CLI 설정 파일 읽기 실패: {e}", file=sys.stderr)
            
            # Azure CLI 설정 파일에서 찾지 못하면 환경 변수 확인
            subscription_id = os.environ.get('AZURE_SUBSCRIPTION_ID')
            if subscription_id:
                if subscription_id.startswith("/subscriptions/"):
                    subscription_id = subscription_id.split("/subscriptions/")[1].split("/")[0]
                return subscription_id
            
            # 위 방법들이 실패하면 Azure Python SDK로 fallback
            from azure.mgmt.resource import SubscriptionClient
            
            # Credential이 없으면 먼저 초기화
            if not self.credential:
                self._ensure_initialized()
            
            if not self.credential:
                return None
            
            # SubscriptionClient로 현재 구독 조회
            subscription_client = SubscriptionClient(self.credential)
            subscriptions = subscription_client.subscriptions.list()
            
            # 첫 번째 활성 구독 반환
            first_sub = None
            for sub in subscriptions:
                if first_sub is None:
                    first_sub = sub
                if sub.state and sub.state.lower() == "enabled":
                    return sub.subscription_id
            
            # 활성 구독이 없으면 첫 번째 구독 반환
            if first_sub:
                return first_sub.subscription_id
            
            return None
        except Exception as e:
            print(f"⚠️ 구독 ID 조회 실패: {e}", file=sys.stderr)
            return None
    
    def get_current_subscription(self) -> Optional[Dict]:
        """현재 구독 정보 조회 (Azure CLI 설정 파일 우선 확인)"""
        try:
            # 먼저 Azure CLI 설정 파일에서 현재 선택된 구독 확인
            import platform
            is_windows = platform.system() == "Windows"
            
            if is_windows:
                azure_profile_path = os.path.join(os.environ.get('USERPROFILE', ''), '.azure', 'azureProfile.json')
            else:
                azure_profile_path = os.path.join(os.path.expanduser('~'), '.azure', 'azureProfile.json')
            
            # Azure CLI 설정 파일 읽기
            if os.path.exists(azure_profile_path):
                try:
                    # UTF-8 BOM 처리 (utf-8-sig 사용)
                    with open(azure_profile_path, 'r', encoding='utf-8-sig') as f:
                        azure_profile = json.load(f)
                    
                    # subscriptions 배열에서 isDefault가 true인 구독 찾기
                    subscriptions = azure_profile.get('subscriptions', [])
                    for sub in subscriptions:
                        if sub.get('isDefault', False):
                            subscription_id = sub.get('id')
                            if subscription_id:
                                # /subscriptions/ 접두사 제거
                                if subscription_id.startswith("/subscriptions/"):
                                    subscription_id = subscription_id.split("/subscriptions/")[1].split("/")[0]
                                
                                # 구독 ID로 상세 정보 조회
                                from azure.mgmt.resource import SubscriptionClient
                                
                                if not self.credential:
                                    self._ensure_initialized()
                                
                                if self.credential:
                                    subscription_client = SubscriptionClient(self.credential)
                                    subscription = subscription_client.subscriptions.get(subscription_id)
                                    
                                    return {
                                        "id": subscription.id,
                                        "subscriptionId": subscription.subscription_id,
                                        "displayName": subscription.display_name,
                                        "tenantId": subscription.tenant_id,
                                        "state": subscription.state,
                                        "name": subscription.display_name
                                    }
                except Exception as e:
                    print(f"⚠️ Azure CLI 설정 파일 읽기 실패: {e}", file=sys.stderr)
            
            # Azure CLI 설정 파일에서 찾지 못하면 Azure Python SDK로 fallback
            from azure.mgmt.resource import SubscriptionClient
            
            # Credential이 없으면 먼저 초기화
            if not self.credential:
                self._ensure_initialized()
            
            if not self.credential:
                return None
            
            # SubscriptionClient로 현재 구독 조회
            subscription_client = SubscriptionClient(self.credential)
            subscriptions = subscription_client.subscriptions.list()
            
            # 첫 번째 활성 구독 반환
            for sub in subscriptions:
                if sub.state and sub.state.lower() == "enabled":
                    return {
                        "id": sub.id,
                        "subscriptionId": sub.subscription_id,
                        "displayName": sub.display_name,
                        "tenantId": sub.tenant_id,
                        "state": sub.state,
                        "name": sub.display_name
                    }
            
            # 활성 구독이 없으면 첫 번째 구독 반환
            subscriptions = subscription_client.subscriptions.list()
            first_sub = next(subscriptions, None)
            if first_sub:
                return {
                    "id": first_sub.id,
                    "subscriptionId": first_sub.subscription_id,
                    "displayName": first_sub.display_name,
                    "tenantId": first_sub.tenant_id,
                    "state": first_sub.state,
                    "name": first_sub.display_name
                }
            
            return None
        
        except Exception as e:
            print(f"⚠️ 구독 정보 조회 실패: {e}", file=sys.stderr)
            return None

    def refresh_auth_status(self, force_check: bool = False) -> bool:
        """인증 상태 재확인 (Azure Python SDK만 사용, Azure CLI 호출 제거)
        
        Args:
            force_check: True면 강제로 재확인, False면 이미 인증된 경우 건너뛰기
        """
        # 빠른 경로: 이미 인증되어 있고 Credential이 있으며, 강제 확인이 아닌 경우
        if not force_check and self.is_authenticated and self.credential:
            print("✅ 인증 상태 확인됨 (이미 인증된 상태, 재확인 건너뜀)", file=sys.stderr)
            return True
        
        # force_check=True이고 이미 인증된 경우: Azure Python SDK로 빠르게 확인
        if force_check and self.is_authenticated and self.credential:
            print("🔄 인증 상태 재확인 중 (빠른 경로)...", file=sys.stderr)
            try:
                from azure.identity import AzureCliCredential
                from azure.core.exceptions import ClientAuthenticationError
                
                # AzureCliCredential로 빠르게 확인
                credential = AzureCliCredential()
                token = credential.get_token("https://management.azure.com/.default")
                
                if token and token.token:
                    print("✅ 인증 상태 확인 완료 (로그인 상태 유지)", file=sys.stderr)
                    return True
                else:
                    print("⚠️ 로그인 상태 변경 감지, 전체 재확인 진행...", file=sys.stderr)
                    self.is_authenticated = False
                    self.credential = None
            except ClientAuthenticationError:
                print("⚠️ 로그인 상태 변경 감지, 전체 재확인 진행...", file=sys.stderr)
                self.is_authenticated = False
                self.credential = None
            except Exception as e:
                print(f"⚠️ 빠른 확인 중 오류, 전체 재확인 진행: {str(e)}", file=sys.stderr)
                self.is_authenticated = False
                self.credential = None
        
        # 실제 확인이 필요한 경우 (인증 안 됨 또는 전체 재확인 필요)
        print("🔄 인증 상태 재확인 중...", file=sys.stderr)
        
        # Azure Python SDK로 직접 인증 확인 (Azure CLI 호출 없이)
        try:
            from azure.identity import AzureCliCredential
            from azure.core.exceptions import ClientAuthenticationError
            
            credential = AzureCliCredential()
            token = credential.get_token("https://management.azure.com/.default")
            
            if token and token.token:
                # 성공 시 DefaultAzureCredential로 전환
                from azure.identity import DefaultAzureCredential
                self.credential = DefaultAzureCredential(
                    exclude_managed_identity_credential=True,
                )
                self.is_authenticated = True
                self.auth_message = "Azure 인증 성공"
                print("✅ 인증 상태 업데이트 완료", file=sys.stderr)
                return True
            else:
                self.is_authenticated = False
                self.credential = None
                self.auth_message = "Azure에 로그인되어 있지 않습니다.\n실행:  az login"
                print("❌ Azure 로그인 안 됨", file=sys.stderr)
                return False
                
        except ClientAuthenticationError as e:
            self.is_authenticated = False
            self.credential = None
            error_msg = str(e)
            if "az login" in error_msg.lower() or "Please run 'az login'" in error_msg:
                self.auth_message = "Azure에 로그인되어 있지 않습니다.\n실행:  az login"
            else:
                self.auth_message = f"인증 실패: {error_msg}"
            print("❌ Azure 로그인 안 됨", file=sys.stderr)
            return False
        except Exception as e:
            self.is_authenticated = False
            self.credential = None
            self.auth_message = f"인증 확인 중 오류: {str(e)}"
            print(f"❌ 인증 확인 실패: {str(e)}", file=sys.stderr)
            return False
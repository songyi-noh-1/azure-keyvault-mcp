import os
import tempfile
from typing import Optional, Tuple, List
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import datetime

class CertificateUtils: 
    """인증서 변환 및 생성 유틸리티"""
    
    @staticmethod
    def _is_encrypted_key(key_data: bytes) -> bool:
        """키 파일이 암호화되어 있는지 확인"""
        key_str = key_data.decode('utf-8', errors='ignore')
        return 'ENCRYPTED' in key_str or 'Proc-Type: 4,ENCRYPTED' in key_str
    
    # ===== PEM 변환 =====
    
    @staticmethod
    def convert_pem_to_pfx(
        cert_pem_path: str,
        key_pem_path: str,
        pfx_password: Optional[str] = None
    ) -> bytes:
        """PEM 형식 (cert + key)을 PFX로 변환"""
        
        # 인증서 로드
        with open(cert_pem_path, 'rb') as f:
            cert_data = f.read()
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        
        # 개인키 로드
        with open(key_pem_path, 'rb') as f:
            key_data = f.read()
            
            # 암호화 여부 확인
            is_encrypted = CertificateUtils._is_encrypted_key(key_data)
            if is_encrypted and not pfx_password:
                raise ValueError("🔒 암호화된 개인키 파일입니다. 비밀번호(password)를 제공해주세요.")
            
            try:
                # 암호화된 키 시도
                key = serialization.load_pem_private_key(
                    key_data,
                    password=pfx_password.encode() if pfx_password else None,
                    backend=default_backend()
                )
            except (ValueError, TypeError) as e:
                if is_encrypted:
                    raise ValueError(f"🔒 암호화된 키 파일의 비밀번호가 올바르지 않습니다: {str(e)}")
                # 암호화 안 된 키
                key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                    backend=default_backend()
                )
        
        # PFX (PKCS12) 생성
        if pfx_password:
            encryption = serialization.BestAvailableEncryption(pfx_password.encode())
        else:
            encryption = serialization.NoEncryption()
        
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=b"certificate",
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=encryption
        )
        
        return pfx_bytes
    
    @staticmethod
    def convert_pem_bytes_to_pfx(
        cert_pem_bytes: bytes,
        key_pem_bytes: bytes,
        pfx_password:  Optional[str] = None
    ) -> bytes:
        """PEM 바이트를 PFX로 변환 (파일 없이)"""
        
        # 인증서 로드
        cert = x509.load_pem_x509_certificate(cert_pem_bytes, default_backend())
        
        # 암호화 여부 확인
        is_encrypted = CertificateUtils._is_encrypted_key(key_pem_bytes)
        if is_encrypted and not pfx_password:
            raise ValueError("🔒 암호화된 개인키 파일입니다. 비밀번호(password)를 제공해주세요.")
        
        # 개인키 로드
        try:
            # 암호화된 키 시도
            key = serialization.load_pem_private_key(
                key_pem_bytes,
                password=pfx_password.encode() if pfx_password else None,
                backend=default_backend()
            )
        except (ValueError, TypeError) as e:
            if is_encrypted:
                raise ValueError(f"🔒 암호화된 키 파일의 비밀번호가 올바르지 않습니다: {str(e)}")
            # 암호화 안 된 키
            key = serialization.load_pem_private_key(
                key_pem_bytes,
                password=None,
                backend=default_backend()
            )
        
        # PFX 생성
        if pfx_password:
            encryption = serialization.BestAvailableEncryption(pfx_password.encode())
        else:
            encryption = serialization.NoEncryption()
        
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=b"certificate",
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=encryption
        )
        
        return pfx_bytes
    
    # ===== CRT/CER 변환 =====
    
    @staticmethod
    def convert_crt_to_pfx(
        cert_crt_path: str,
        key_path: str,
        pfx_password: Optional[str] = None
    ) -> bytes:
        """CRT/CER 형식 (+ 개인키)을 PFX로 변환"""
        
        # CRT는 DER 또는 PEM 형식일 수 있음
        with open(cert_crt_path, 'rb') as f:
            cert_data = f. read()
        
        # DER 형식 시도
        try:
            cert = x509.load_der_x509_certificate(cert_data, default_backend())
        except ValueError:
            # PEM 형식 시도
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        
        # 개인키 로드
        with open(key_path, 'rb') as f:
            key_data = f.read()
        
        # DER 형식 키 시도
        try:
            key = serialization.load_der_private_key(
                key_data,
                password=pfx_password.encode() if pfx_password else None,
                backend=default_backend()
            )
        except ValueError:
            # PEM 형식 키 시도
            try:
                key = serialization. load_pem_private_key(
                    key_data,
                    password=pfx_password.encode() if pfx_password else None,
                    backend=default_backend()
                )
            except TypeError: 
                key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                    backend=default_backend()
                )
        
        # PFX 생성
        if pfx_password:
            encryption = serialization.BestAvailableEncryption(pfx_password.encode())
        else:
            encryption = serialization.NoEncryption()
        
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=b"certificate",
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=encryption
        )
        
        return pfx_bytes
    
    @staticmethod
    def convert_crt_bytes_to_pfx(
        cert_crt_bytes: bytes,
        key_bytes: bytes,
        pfx_password: Optional[str] = None
    ) -> bytes:
        """CRT 바이트를 PFX로 변환"""
        
        # CRT 로드 (DER 또는 PEM)
        try:
            cert = x509.load_der_x509_certificate(cert_crt_bytes, default_backend())
        except ValueError:
            cert = x509.load_pem_x509_certificate(cert_crt_bytes, default_backend())
        
        # 개인키 로드
        try:
            key = serialization. load_der_private_key(
                key_bytes,
                password=pfx_password.encode() if pfx_password else None,
                backend=default_backend()
            )
        except ValueError:
            try:
                key = serialization.load_pem_private_key(
                    key_bytes,
                    password=pfx_password.encode() if pfx_password else None,
                    backend=default_backend()
                )
            except TypeError:
                key = serialization. load_pem_private_key(
                    key_bytes,
                    password=None,
                    backend=default_backend()
                )
        
        # PFX 생성
        pfx_bytes = serialization. pkcs12.serialize_key_and_certificates(
            name=b"certificate",
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(
                pfx_password.encode() if pfx_password else b""
            )
        )
        
        return pfx_bytes
    
    # ===== 체인 인증서 지원 =====
    
    @staticmethod
    def convert_with_chain_to_pfx(
        cert_path: str,
        key_path: str,
        chain_paths: List[str],
        pfx_password: Optional[str] = None
    ) -> bytes:
        """인증서 + 개인키 + 중간 인증서 체인을 PFX로 변환"""
        
        # 주 인증서 로드
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
            try:
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            except ValueError: 
                cert = x509.load_der_x509_certificate(cert_data, default_backend())
        
        # 개인키 로드
        with open(key_path, 'rb') as f:
            key_data = f.read()
            
            # 암호화 여부 확인
            is_encrypted = CertificateUtils._is_encrypted_key(key_data)
            if is_encrypted and not pfx_password:
                raise ValueError("🔒 암호화된 개인키 파일입니다. 비밀번호(password)를 제공해주세요.")
            
            try:
                key = serialization.load_pem_private_key(
                    key_data,
                    password=pfx_password.encode() if pfx_password else None,
                    backend=default_backend()
                )
            except (ValueError, TypeError) as e:
                if is_encrypted:
                    raise ValueError(f"🔒 암호화된 키 파일의 비밀번호가 올바르지 않습니다: {str(e)}")
                key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                    backend=default_backend()
                )
        
        # 중간 인증서 로드
        chain_certs = []
        for chain_path in chain_paths: 
            with open(chain_path, 'rb') as f:
                chain_data = f.read()
                try:
                    chain_cert = x509.load_pem_x509_certificate(chain_data, default_backend())
                except ValueError:
                    chain_cert = x509.load_der_x509_certificate(chain_data, default_backend())
                chain_certs.append(chain_cert)
        
        # PFX 생성 (체인 포함)
        if pfx_password:
            encryption = serialization.BestAvailableEncryption(pfx_password.encode())
        else:
            encryption = serialization.NoEncryption()
        
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=b"certificate",
            key=key,
            cert=cert,
            cas=chain_certs if chain_certs else None,
            encryption_algorithm=encryption
        )
        
        return pfx_bytes
    
    # ===== 번들 파일 처리 (cert + key가 하나의 파일에) =====
    
    @staticmethod
    def convert_bundle_pem_to_pfx(
        bundle_pem_path:  str,
        pfx_password: Optional[str] = None
    ) -> bytes:
        """하나의 PEM 파일에 인증서와 개인키가 모두 있는 경우"""
        
        with open(bundle_pem_path, 'rb') as f:
            bundle_data = f. read()
        
        return CertificateUtils.convert_bundle_pem_bytes_to_pfx(bundle_data, pfx_password)
    
    @staticmethod
    def convert_bundle_pem_bytes_to_pfx(
        bundle_pem_bytes: bytes,
        pfx_password: Optional[str] = None
    ) -> bytes:
        """번들 PEM 바이트를 PFX로 변환"""
        
        # PEM 데이터를 파싱하여 인증서와 키 분리
        bundle_str = bundle_pem_bytes. decode('utf-8')
        
        # 인증서 추출
        cert_start = bundle_str.find('-----BEGIN CERTIFICATE-----')
        cert_end = bundle_str.find('-----END CERTIFICATE-----') + len('-----END CERTIFICATE-----')
        cert_pem = bundle_str[cert_start:cert_end]. encode('utf-8')
        cert = x509.load_pem_x509_certificate(cert_pem, default_backend())
        
        # 개인키 추출 (여러 형식 지원)
        key = None
        for key_header in [
            '-----BEGIN PRIVATE KEY-----',
            '-----BEGIN RSA PRIVATE KEY-----',
            '-----BEGIN EC PRIVATE KEY-----',
            '-----BEGIN ENCRYPTED PRIVATE KEY-----'
        ]:
            if key_header in bundle_str:
                key_start = bundle_str.find(key_header)
                # 해당 END 태그 찾기
                end_tag = key_header.replace('BEGIN', 'END')
                key_end = bundle_str.find(end_tag) + len(end_tag)
                key_pem = bundle_str[key_start:key_end].encode('utf-8')
                
                try:
                    key = serialization.load_pem_private_key(
                        key_pem,
                        password=pfx_password.encode() if pfx_password else None,
                        backend=default_backend()
                    )
                    break
                except TypeError:
                    key = serialization.load_pem_private_key(
                        key_pem,
                        password=None,
                        backend=default_backend()
                    )
                    break
        
        if not key:
            raise ValueError("개인키를 찾을 수 없습니다")
        
        # 중간 인증서도 추출 (있다면)
        chain_certs = []
        remaining = bundle_str[cert_end:]
        while '-----BEGIN CERTIFICATE-----' in remaining:
            cert_start = remaining.find('-----BEGIN CERTIFICATE-----')
            cert_end = remaining.find('-----END CERTIFICATE-----') + len('-----END CERTIFICATE-----')
            chain_pem = remaining[cert_start: cert_end].encode('utf-8')
            chain_cert = x509.load_pem_x509_certificate(chain_pem, default_backend())
            chain_certs.append(chain_cert)
            remaining = remaining[cert_end:]
        
        # PFX 생성
        if pfx_password:
            encryption = serialization.BestAvailableEncryption(pfx_password.encode())
        else:
            encryption = serialization.NoEncryption()
        
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=b"certificate",
            key=key,
            cert=cert,
            cas=chain_certs if chain_certs else None,
            encryption_algorithm=encryption
        )
        
        return pfx_bytes
    
    # ===== 유틸리티 =====
    
    @staticmethod
    def read_file(file_path: str) -> bytes:
        """파일 읽기"""
        with open(file_path, 'rb') as f:
            return f. read()
    
    @staticmethod
    def detect_format(cert_bytes: bytes) -> str:
        """인증서 형식 감지"""
        cert_str = cert_bytes.decode('utf-8', errors='ignore')
        
        if '-----BEGIN CERTIFICATE-----' in cert_str:
            return 'PEM'
        elif cert_bytes[0:1] == b'\x30':  # ASN.1 시퀀스 시작
            return 'DER'
        else:
            return 'UNKNOWN'
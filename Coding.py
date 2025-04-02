from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def normalize_key_to_32_bytes(key: str) -> bytes:
    if isinstance(key, str):
        key = key.encode('utf-8')
    return hashlib.sha256(key).digest()  # Возвращает 32 байта

def encrypt_aes256(text: str, key: str) -> str:
    key_bytes = normalize_key_to_32_bytes(key)
    iv = get_random_bytes(AES.block_size)  # Генерируем IV
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))
    return base64.b64encode(iv + encrypted).decode('utf-8')

def decrypt_aes256(encrypted_text: str, key: str) -> str:
    key_bytes = normalize_key_to_32_bytes(key)
    data = base64.b64decode(encrypted_text)
    iv, ciphertext = data[:AES.block_size], data[AES.block_size:]
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return decrypted.decode('utf-8')